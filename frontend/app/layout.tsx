import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/ui/ThemeProvider';
import { FestiveDoodleBackground } from '@/components/ui/FestiveDoodleBackground';

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
    <html lang="en" className="scroll-smooth" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,400&family=Rozha+One&display=swap"
          rel="stylesheet"
        />
        {/* Anti-FOUC Theme Script */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var saved = localStorage.getItem('utsav-theme');
                  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  if (saved === 'dark' || (!saved && prefersDark)) {
                    document.documentElement.classList.add('dark');
                  } else {
                    document.documentElement.classList.remove('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-screen bg-[#FAF7F2] dark:bg-[#0C0E12] text-stone-900 dark:text-stone-100 transition-colors duration-200 relative antialiased selection:bg-amber-200 dark:selection:bg-amber-900/50">
        <ThemeProvider>
          {/* Festive Background Doodles across all pages */}
          <FestiveDoodleBackground />

          {/* Main Application Container */}
          <div className="relative z-10">
            {children}
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
