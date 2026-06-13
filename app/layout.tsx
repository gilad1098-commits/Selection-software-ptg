import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "PTG AHU Selection Software",
  description: "HVAC Air Handling Unit configuration and pricing system for Pach Taas",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-[#181C22] text-[#E8E8E8]">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
