import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Employee — AI Receptionist for Trade Businesses",
  description:
    "Fair launch: AI receptionist that answers calls, books jobs, and updates your CRM. Built for plumbers, gas engineers, mechanics, and 14+ trades.",
  openGraph: {
    title: "AI Employee — Never miss a lead",
    description:
      "24/7 AI receptionist for trade businesses. Answers calls, books appointments, sends confirmations.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
