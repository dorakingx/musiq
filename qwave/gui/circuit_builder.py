"""
Quantum Circuit Builder Module

This module provides a visual quantum circuit builder widget that allows users
to construct quantum circuits by placing gates on qubits.
"""

import tkinter as tk
from tkinter import ttk
from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps
from typing import List, Optional


class CircuitBuilderWidget(tk.Canvas):
    """
    Visual quantum circuit builder widget.
    
    Allows users to place quantum gates on qubits by clicking on the canvas.
    Supports common gates: H, X, Y, Z, CNOT, CZ, T, S, and measurement.
    """
    
    # Gate definitions: (name, color, width, symbol)
    GATES = {
        'H': ('H', '#4CAF50', 1, 'H'),
        'X': ('X', '#F44336', 1, 'X'),
        'Y': ('Y', '#FF9800', 1, 'Y'),
        'Z': ('Z', '#2196F3', 1, 'Z'),
        'T': ('T', '#9C27B0', 1, 'T'),
        'S': ('S', '#00BCD4', 1, 'S'),
        'CNOT': ('CNOT', '#E91E63', 2, '⊕'),
        'CZ': ('CZ', '#673AB7', 2, '•'),
        'M': ('M', '#607D8B', 1, 'M'),
    }
    
    def __init__(self, parent, num_qubits: int = 5, qubit_spacing: int = 60, 
                 gate_width: int = 50, gate_height: int = 40, **kwargs):
        """
        Initialize the circuit builder widget.
        
        Args:
            parent: Parent widget
            num_qubits: Number of qubits in the circuit
            qubit_spacing: Vertical spacing between qubits
            gate_width: Width of gate boxes
            gate_height: Height of gate boxes
        """
        super().__init__(parent, **kwargs)
        
        self.num_qubits = num_qubits
        self.qubit_spacing = qubit_spacing
        self.gate_width = gate_width
        self.gate_height = gate_height
        self.column_width = gate_width + 20
        self.top_margin = 30
        
        # Circuit state: list of gates per qubit
        # Each gate is (column, gate_type, control_qubit if applicable)
        self.circuit_state = [[] for _ in range(num_qubits)]
        self.max_column = 0
        self.hover_column = None
        self.hover_qubit = None
        
        # Selected gate for placement
        self.selected_gate = None
        self.erase_mode = False
        
        # Bind events
        self.bind('<Button-1>', self.on_click)
        self.bind('<Motion>', self.on_motion)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Configure>', self.on_resize)
        
        # Draw initial circuit
        self.draw_circuit()
    
    def set_selected_gate(self, gate_type: Optional[str]):
        """Set the currently selected gate for placement."""
        if gate_type == 'ERASE':
            self.erase_mode = True
            self.selected_gate = None
        else:
            self.erase_mode = False
            self.selected_gate = gate_type
    
    def on_click(self, event):
        """Handle mouse click to place gates."""
        if self.selected_gate is None and not self.erase_mode:
            return
        
        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)
        click_x = canvas_x - 50
        if click_x < 0:
            return
        
        y_pos = canvas_y - self.top_margin
        if y_pos < 0:
            return
        qubit = int(y_pos / self.qubit_spacing)
        column = int(click_x / self.column_width)
        
        if 0 <= qubit < self.num_qubits and column >= 0:
            if self.erase_mode:
                self.remove_gates_in_column([qubit, qubit + 1] if qubit + 1 < self.num_qubits else [qubit], column)
                self.draw_circuit()
                return
            self.place_gate(qubit, column, self.selected_gate)
    
    def on_motion(self, event):
        """Track cursor position for hover indication."""
        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)
        click_x = canvas_x - 50
        y_pos = canvas_y - self.top_margin
        column = int(click_x / self.column_width) if click_x >= 0 else None
        qubit = int(y_pos / self.qubit_spacing) if y_pos >= 0 else None
        if qubit is not None and (qubit < 0 or qubit >= self.num_qubits):
            qubit = None
        if column is not None and column < 0:
            column = None
        if column != self.hover_column or qubit != self.hover_qubit:
            self.hover_column = column
            self.hover_qubit = qubit
            self.draw_circuit()
    
    def on_leave(self, _event):
        """Clear hover indicators when cursor leaves canvas."""
        if self.hover_column is not None or self.hover_qubit is not None:
            self.hover_column = None
            self.hover_qubit = None
            self.draw_circuit()
    
    def place_gate(self, qubit: int, column: int, gate_type: str):
        """
        Place a gate on the circuit.
        
        Args:
            qubit: Qubit index (0-based)
            column: Column position
            gate_type: Type of gate to place
        """
        if gate_type not in self.GATES:
            return
        
        gate_info = self.GATES[gate_type]
        gate_width = gate_info[2]

        # Toggle off if same gate already present at this location
        for c, g, t in self.circuit_state[qubit]:
            if c == column and g == gate_type:
                self._remove_gate_at(qubit, column, gate_type)
                self.draw_circuit()
                return
        
        # For two-qubit gates, need to handle control qubit
        if gate_width == 2:
            # For CNOT/CZ, use the next qubit as target
            if qubit + 1 < self.num_qubits:
                # Remove any existing gates in this column for these qubits
                self.remove_gates_in_column([qubit, qubit + 1], column)
                self.circuit_state[qubit].append((column, gate_type, qubit + 1))
                self.circuit_state[qubit + 1].append((column, gate_type, qubit))
            else:
                return
        else:
            # Single-qubit gate
            self.remove_gates_in_column([qubit], column)
            self.circuit_state[qubit].append((column, gate_type, None))
        
        self.max_column = max(self.max_column, column + 1)
        self.draw_circuit()
    
    def remove_gates_in_column(self, qubits: List[int], column: int):
        """Remove gates in a specific column for given qubits."""
        for q in qubits:
            self.circuit_state[q] = [
                (c, g, t) for c, g, t in self.circuit_state[q] 
                if c != column
            ]

    def _remove_gate_at(self, qubit: int, column: int, gate_type: str):
        """Remove a specific gate (and its partner) at column."""
        partner = None
        new_entries = []
        for c, g, t in self.circuit_state[qubit]:
            if c == column and g == gate_type:
                partner = t
                continue
            new_entries.append((c, g, t))
        self.circuit_state[qubit] = new_entries
        if partner is not None and 0 <= partner < self.num_qubits:
            self.circuit_state[partner] = [
                (c, g, t) for c, g, t in self.circuit_state[partner]
                if not (c == column and g == gate_type and t == qubit)
            ]
    
    def clear_circuit(self):
        """Clear the entire circuit."""
        self.circuit_state = [[] for _ in range(self.num_qubits)]
        self.max_column = 0
        self.draw_circuit()
    
    def draw_circuit(self):
        """Draw the quantum circuit on the canvas."""
        self.delete("all")
        
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        self._draw_column_grid(width)
        
        # Draw qubit lines
        for i in range(self.num_qubits):
            y = self.top_margin + i * self.qubit_spacing + self.qubit_spacing // 2
            self.create_line(0, y, width, y, fill='gray', width=2, tags='qubit_line')
            self.create_text(10, y, text=f'q[{i}]', anchor='w', tags='qubit_label')
        
        # Draw gates
        for qubit in range(self.num_qubits):
            for column, gate_type, target_qubit in self.circuit_state[qubit]:
                # Only draw if this is the primary qubit (not target of 2-qubit gate)
                if target_qubit is None or qubit < target_qubit:
                    self.draw_gate(qubit, column, gate_type, target_qubit)
        
        self._draw_hover_indicator()
    
        # Update scroll region
        self.configure(scrollregion=self.bbox("all"))
    
    def _draw_column_grid(self, width: int):
        """Draw vertical guides and column numbers."""
        max_cols = max(self.max_column + 4, max(16, int((width - 50) / self.column_width)))
        for col in range(max_cols + 1):
            x = col * self.column_width + 50
            color = '#e0e0e0' if col % 2 == 0 else '#f0f0f0'
            self.create_line(
                x,
                self.top_margin / 2,
                x,
                self.top_margin + self.num_qubits * self.qubit_spacing,
                fill=color,
                width=1,
                dash=(2, 4)
            )
            if col % 2 == 0:
                self.create_text(x, 12, text=str(col), fill='#555555', font=('Arial', 8))
    
    def _draw_hover_indicator(self):
        """Render hover highlight for column/qubit."""
        if self.hover_column is None:
            return
        x_start = self.hover_column * self.column_width + 50
        x_end = x_start + self.column_width
        y_start = self.top_margin
        y_end = self.top_margin + self.num_qubits * self.qubit_spacing
        self.create_rectangle(
            x_start, y_start, x_end, y_end,
            fill='#d1e3ff', outline='', stipple='gray50'
        )
        if self.hover_qubit is not None and 0 <= self.hover_qubit < self.num_qubits:
            q_y_start = self.top_margin + self.hover_qubit * self.qubit_spacing
            q_y_end = q_y_start + self.qubit_spacing
            self.create_rectangle(
                x_start, q_y_start, x_end, q_y_end,
                outline='#1a73e8', width=2
            )
            if self.erase_mode:
                self.create_text((x_start + x_end) / 2, (q_y_start + q_y_end) / 2,
                                 text="×", fill="#d32f2f", font=('Arial', 24, 'bold'))
            elif self.selected_gate:
                gate_info = self.GATES.get(self.selected_gate)
                if gate_info:
                    gate_width = gate_info[2]
                    if gate_width == 1 or (gate_width == 2 and self.hover_qubit + 1 < self.num_qubits):
                        self.draw_preview_gate(self.hover_qubit, self.hover_column, self.selected_gate)
    
    def draw_gate(self, qubit: int, column: int, gate_type: str, target_qubit: Optional[int]):
        """Draw a single gate on the canvas."""
        gate_info = self.GATES[gate_type]
        gate_name, color, gate_width, symbol = gate_info
        
        x = column * self.column_width + 50 + self.column_width / 2
        y = self.top_margin + qubit * self.qubit_spacing + self.qubit_spacing // 2
        
        if gate_width == 2 and target_qubit is not None:
            # Two-qubit gate (CNOT or CZ)
            target_y = self.top_margin + target_qubit * self.qubit_spacing + self.qubit_spacing // 2
            
            # Draw control line
            self.create_line(x, y, x, target_y, fill=color, width=3, tags='gate')
            
            # Draw control dot/circle
            if gate_type == 'CNOT':
                self.create_oval(x - 8, y - 8, x + 8, y + 8, 
                               fill=color, outline=color, tags='gate')
            else:  # CZ
                self.create_oval(x - 8, y - 8, x + 8, y + 8, 
                               fill=color, outline=color, width=3, tags='gate')
            
            # Draw target
            if gate_type == 'CNOT':
                self.create_oval(x - 12, target_y - 12, x + 12, target_y + 12,
                               outline=color, width=3, tags='gate')
                self.create_line(x - 8, target_y, x + 8, target_y, 
                               fill=color, width=2, tags='gate')
                self.create_line(x, target_y - 8, x, target_y + 8,
                               fill=color, width=2, tags='gate')
            else:  # CZ
                self.create_oval(x - 8, target_y - 8, x + 8, target_y + 8,
                               fill=color, outline=color, width=3, tags='gate')
        else:
            # Single-qubit gate
            gate_rect = self.create_rectangle(
                x - self.gate_width // 2, y - self.gate_height // 2,
                x + self.gate_width // 2, y + self.gate_height // 2,
                fill=color, outline='black', width=2, tags='gate'
            )
            self.create_text(x, y, text=symbol, fill='white', 
                           font=('Arial', 12, 'bold'), tags='gate')

    def draw_preview_gate(self, qubit: int, column: int, gate_type: str):
        """Draw translucent preview of gate placement."""
        gate_info = self.GATES[gate_type]
        _, color, gate_width, symbol = gate_info
        x = column * self.column_width + 50 + self.column_width / 2
        y = self.top_margin + qubit * self.qubit_spacing + self.qubit_spacing // 2
        if gate_width == 2:
            target_qubit = qubit + 1
            target_y = self.top_margin + target_qubit * self.qubit_spacing + self.qubit_spacing // 2
            self.create_line(x, y, x, target_y, fill=color, width=2, dash=(4, 4))
            self.create_oval(x - 8, y - 8, x + 8, y + 8,
                             outline=color, width=2, dash=(4, 4))
            self.create_oval(x - 8, target_y - 8, x + 8, target_y + 8,
                             outline=color, width=2, dash=(4, 4))
            if gate_type == 'CNOT':
                self.create_line(x - 8, target_y, x + 8, target_y,
                                 fill=color, width=1, dash=(4, 4))
                self.create_line(x, target_y - 8, x, target_y + 8,
                                 fill=color, width=1, dash=(4, 4))
        else:
            rect = self.create_rectangle(
                x - self.gate_width // 2, y - self.gate_height // 2,
                x + self.gate_width // 2, y + self.gate_height // 2,
                outline=color, width=2, dash=(3, 3), fill=''
            )
            self.create_text(x, y, text=symbol, fill=color,
                             font=('Arial', 12, 'bold'))
    
    def on_resize(self, event):
        """Handle widget resize."""
        self.draw_circuit()
    
    def to_qiskit_circuit(self) -> QuantumCircuit:
        """
        Convert the visual circuit to a Qiskit QuantumCircuit.
        
        Returns:
            QuantumCircuit object
        """
        circuit = QuantumCircuit(self.num_qubits, self.num_qubits)
        
        # Collect all gates sorted by column
        all_gates = []
        for qubit in range(self.num_qubits):
            for column, gate_type, target_qubit in self.circuit_state[qubit]:
                if target_qubit is None or qubit < target_qubit:
                    all_gates.append((column, qubit, gate_type, target_qubit))
        
        # Sort by column
        all_gates.sort(key=lambda x: x[0])
        
        # Apply gates in order
        for column, qubit, gate_type, target_qubit in all_gates:
            if gate_type == 'H':
                circuit.h(qubit)
            elif gate_type == 'X':
                circuit.x(qubit)
            elif gate_type == 'Y':
                circuit.y(qubit)
            elif gate_type == 'Z':
                circuit.z(qubit)
            elif gate_type == 'T':
                circuit.t(qubit)
            elif gate_type == 'S':
                circuit.s(qubit)
            elif gate_type == 'CNOT' and target_qubit is not None:
                circuit.cx(qubit, target_qubit)
            elif gate_type == 'CZ' and target_qubit is not None:
                circuit.cz(qubit, target_qubit)
            elif gate_type == 'M':
                circuit.measure(qubit, qubit)
        
        return circuit
    
    def save_to_qasm(self, filepath: str):
        """Save the circuit to a QASM file."""
        circuit = self.to_qiskit_circuit()
        with open(filepath, 'w') as f:
            f.write(dumps(circuit))





