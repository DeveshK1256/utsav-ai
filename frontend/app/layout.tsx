import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Utsav (उत्सव) — Celebrations, Composed.',
  description: 'Intelligent, culture-native GenAI event orchestration platform for Indian celebrations.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,600;1,400&family=Rozha+One&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-[#FAF7F2] dark:bg-[#0C0F14] text-stone-900 dark:text-stone-100 transition-colors duration-200">
        {children}
      </body>
    </html>
  );
}
