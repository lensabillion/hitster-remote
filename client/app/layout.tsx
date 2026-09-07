import type { Metadata } from "next";
import { Abyssinica_SIL, Noto_Sans_Ethiopic } from "next/font/google";
import "./globals.css";

// Display. One weight only, so it is used at size and never carries hierarchy.
const display = Abyssinica_SIL({
  weight: "400",
  subsets: ["latin", "ethiopic"],
  variable: "--font-display",
  display: "swap",
});

// Text and UI. Variable 100-900 -- every weight step in the interface comes
// from here, which is why the display face can stay single-weight.
const text = Noto_Sans_Ethiopic({
  subsets: ["latin", "ethiopic"],
  variable: "--font-text",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ዜማ · Zema",
  description:
    "A remote music timeline game for Amharic songs. Hear a song, guess the year, build your timeline.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${text.variable}`}>{children}</body>
    </html>
  );
}
