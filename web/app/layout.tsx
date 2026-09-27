import "./globals.css";

export const metadata = {
  title: "Foresight — evidence you can follow",
  description:
    "Strategic foresight briefs for UAE defence, assembled from a governed evidence graph. Every claim traces to the exact words of its source.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Instrument+Sans:wght@400;500;600&display=swap" />
      </head>
      <body>{children}</body>
    </html>
  );
}
