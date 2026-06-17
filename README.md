# Musiq

**Quantum Sonic Studio for composing quantum circuits and rendering non-classical audio.**

Musiq turns OpenQASM / visual quantum circuits into WAV audio, waveform previews,
frequency-spectrum previews, and spectral analysis reports. The current primary
experience is a polished browser workspace deployed on Vercel.

- Production: https://musiquantum.vercel.app/
- Repository: https://github.com/dorakingx/musiq

## What You Can Do

- Build small circuits visually with `H`, `X`, `Y`, `Z`, `T`, `S`, `CNOT`, `CZ`, and measurement gates.
- Switch between Visual view and Code (QASM) view.
- Load bundled OpenQASM examples from the template catalog.
- Import and export `.qasm` circuits.
- Generate audio from a visual circuit or pasted QASM.
- Play, seek, stop, and download generated WAV audio.
- Inspect waveform and spectrum output in the browser.
- Open the Analysis drawer for spectral metrics and the session log.
- Choose compute backends:
  - Local Ideal Simulator (default)
  - IonQ Simulator
  - IonQ QPU (Hardware)

## Quick Start

### Web UI

```bash
npm install
npm run dev
```

Open http://localhost:3000.

The local Next.js dev server is useful for UI and template work. Full audio generation
uses the Python serverless API under `api/`, so use Vercel or `vercel dev` when you
need production-like API behavior locally.

```bash
npx vercel dev
```

### Production Build

```bash
npm run build
npm run start
```

`npm run build` runs `scripts/sync-circuit-templates.mjs` first. That script copies
web-loadable QASM templates into `public/circuit-templates/` and writes the template
manifest used by the browser app.

## Environment Variables

Create `.env` for local secrets:

```bash
IONQ_API_KEY=your_api_key_here
```

On Vercel, set `IONQ_API_KEY` in Project Settings -> Environment Variables.

If `IONQ_API_KEY` is missing and a user selects an IonQ backend, Musiq falls back to
the Local Ideal Simulator and reports the fallback in the session log.

## Browser Workflow

1. Select a gate in **Build Controls**.
2. Place gates on the visual lattice, or switch to **Code (QASM) view** and paste OpenQASM.
3. Set qubits, duration, sample rate, shots, and backend.
4. Click **Generate audio**.
5. Review the waveform first, then the spectrum below it.
6. Use the player to listen, seek, stop, or download the generated WAV.
7. Open **Analysis** for spectral metrics and the session log.

### Current Limits

| Setting | Range |
| --- | --- |
| Visual editor qubits | 2-10 |
| Duration | 0.5-60 seconds |
| Sample rates | 22,050 / 44,100 / 48,000 / 96,000 Hz |
| Shots | 128-8,192 |
| Web-loadable QASM template size | 2 MB max |

Large templates can remain listed in the manifest but are intentionally not served to
the browser when they exceed the web editor size limit.

## QASM Templates

Reference circuits live in `circuits/`. Build-time web templates are copied into
`public/circuit-templates/`.

The current bundled web catalog includes examples such as:

- Bell State (2Q)
- GHZ State (3Q)
- Simple Entangled (3Q)
- Ring Entangle (4Q)
- Example IQP (4Q)
- IQP Circuit (8Q, 16Q, 20Q, 24Q, 56Q)
- Quantum Walk (8Q)
- Hadamard + Measure (8Q)
- Mixed Gates (5Q)

Quantum Walk templates that use custom or multi-controlled gates may be QASM-only in
the browser lattice. They can still be inspected in Code view and used for generation
when they are within the web-loadable size limit.

To refresh the web catalog manually:

```bash
node scripts/sync-circuit-templates.mjs
```

## API Overview

| Endpoint | Runtime | Purpose |
| --- | --- | --- |
| `POST /api/templates` | Next.js route | List or read bundled QASM templates |
| `POST /api/circuit` | Python serverless | Import/export visual circuits as QASM |
| `POST /api/generate_audio` | Python serverless | Simulate the circuit and return audio + analysis |
| `GET /health` | Python serverless rewrite | Basic health check |

`/api/generate_audio` returns base64 WAV audio, waveform preview points, spectrum
preview data, spectral metrics, backend status, and generation logs.

## Local Python Tools

The original Q-Wave Python tooling is still available for local research and desktop
workflows.

### Install Python Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

For Vercel/Python API dependencies only:

```bash
pip install -r api/requirements.txt
```

### CLI

```bash
python qwave_run.py -c circuits/example_iqp_4q.qasm -o output.wav
```

Useful options:

| Argument | Short | Default | Description |
| --- | --- | --- | --- |
| `--circuit` | `-c` | required | Input QASM circuit |
| `--output` | `-o` | required | Output WAV path |
| `--duration` | `-d` | `5.0` | Audio duration in seconds |
| `--samplerate` | `-s` | `44100` | Audio sample rate |
| `--shots` | | `1024` | Quantum measurement shots |
| `--no-analysis` | | `false` | Skip spectral analysis |

Example:

```bash
python qwave_run.py \
  -c circuits/simple_entangled_3q.qasm \
  -o generated_audio/simple_entangled.wav \
  -d 3 \
  -s 48000 \
  --shots 4096
```

### Desktop GUI

```bash
python qwave_gui.py
```

The desktop GUI is a Tkinter-based local tool for visual circuit building, waveform
generation, playback, and saved WAV output. The browser app is the recommended user
experience for the hosted product.

## Project Structure

```text
.
├── app/                         # Next.js app router UI
│   ├── api/templates/route.ts   # Template catalog API
│   ├── components/              # Audio player, icons, analysis drawer
│   ├── globals.css              # Product styling
│   ├── layout.tsx
│   └── page.tsx                 # Main browser workspace
├── api/                         # Vercel Python serverless functions
│   ├── circuit.py
│   ├── generate_audio.py
│   └── health.py
├── lib/                         # TypeScript helpers and types
├── public/                      # Web assets and bundled QASM templates
├── scripts/                     # Build-time template sync
├── qwave/                       # Python quantum/audio package
│   ├── modules/                 # Audio generation and analysis modules
│   ├── gui/                     # Tkinter desktop GUI
│   ├── utils/                   # Backend and audio mapping helpers
│   └── web/                     # Web API pipeline and QASM helpers
├── circuits/                    # Reference OpenQASM circuits
├── qwave_run.py                 # CLI entry point
├── qwave_gui.py                 # Desktop GUI entry point
├── vercel.json                  # Vercel function and rewrite config
└── README.md
```

## Deployment

The production site is deployed by Vercel from `main`.

Typical release flow:

```bash
git status
npm run build
git add <changed files>
git commit -m "Describe the change"
git push origin main
```

Vercel automatically builds and aliases the production deployment to:

```text
https://musiquantum.vercel.app/
```

## How Audio Generation Works

1. The app receives either visual circuit JSON or OpenQASM 2.0.
2. The circuit is simulated locally or submitted to IonQ for measurement shots.
3. Quantum probabilities and measurement sequences are mapped into audio features.
4. A WAV buffer is generated and returned to the browser as base64.
5. The browser renders waveform and spectrum previews and exposes the WAV for download.

The generated audio is experimental. It is designed to expose quantum-inspired
interference and modulation behavior, not to guarantee conventional musical output.

## Troubleshooting

### Template API returns 404 or invalid data

Restart the dev server and make sure templates have been synced:

```bash
node scripts/sync-circuit-templates.mjs
npm run dev
```

### IonQ backend falls back to local simulation

Set `IONQ_API_KEY` locally or in Vercel environment variables.

### Visual view is disabled

The visual editor supports up to 10 qubits. Larger QASM programs can still be edited
and generated from Code (QASM) view when they are otherwise supported by the API.

### Local generation fails in `npm run dev`

Use `vercel dev` for local testing of Vercel Python serverless functions, or use the
Python CLI directly for local renders.

## License

This project is released under the MIT License.

## Acknowledgments

Musiq builds on the Q-Wave quantum audio research workflow and receives support from
the Quantum Creative Challenge.
