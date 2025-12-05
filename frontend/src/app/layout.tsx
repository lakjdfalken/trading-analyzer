import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/Header";
import { ThemeProvider } from "next-themes";
import { AppProvider } from "@/components/providers/AppProvider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Trading Analyzer",
  description:
    "Professional trading analysis and performance tracking dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <AppProvider>
            <div className="min-h-screen bg-background text-foreground">
              <Header />
              <main>{children}</main>
            </div>
          </AppProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
