import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Musiq — Quantum Circuit Audio Generator",
  description: "Build quantum circuits and generate non-classical audio patterns in the browser.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
