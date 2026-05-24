import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DESi Workbench",
  description: "Epistemic-audit assistant that makes DESi visible. Not a peer reviewer.",
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
