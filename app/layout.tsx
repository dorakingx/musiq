import type { Metadata } from "next";
import { DM_Sans, JetBrains_Mono, Syne } from "next/font/google";
import "./globals.css";

const display = Syne({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700", "800"],
});

const body = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Musiq — Quantum Sonic Studio",
  description: "Compose quantum circuits and sculpt non-classical audio in the browser.",
  icons: {
    icon: "/musiq_logo.png",
    apple: "/musiq_logo.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body>
        <div className="ambient" aria-hidden="true">
          <div className="ambient__orb ambient__orb--violet" />
          <div className="ambient__orb ambient__orb--rose" />
          <div className="ambient__orb ambient__orb--cyan" />
        </div>
        {children}
      </body>
    </html>
  );
}
