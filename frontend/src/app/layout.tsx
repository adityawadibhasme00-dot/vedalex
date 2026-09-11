import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'IP-SAKTI | Ayurveda IP & Regulatory Decision Engine',
  description:
    'IP-SAKTI — Multilingual, RAG-based AI assistant for Intellectual Property and regulatory guidance in Ayurveda, across national and international regimes.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-emerald-500 selection:text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
