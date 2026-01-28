import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AdWolf - Reklam Platformlarınızı Birleştirin",
  description: "Google Ads, Meta Ads ve daha fazlasını tek yerden yönetin. AI-powered insights ile performansınızı artırın.",
  keywords: ["dijital pazarlama", "google ads", "meta ads", "reklam yönetimi", "ai", "dashboard"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
