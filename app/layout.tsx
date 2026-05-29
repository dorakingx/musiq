import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Q-Wave: Quantum Circuit Audio Generator",
  description: "Build quantum circuits and generate non-classical audio patterns.",
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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
