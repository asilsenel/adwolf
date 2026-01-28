import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, BarChart3, Sparkles, Zap, Users } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-cream-light">
      {/* Header/Nav */}
      <header className="px-6 py-4 flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-white font-bold text-xl">A</span>
          </div>
          <span className="font-bold text-xl">AdWolf</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login">
            <Button variant="ghost">Giriş Yap</Button>
          </Link>
          <Link href="/register">
            <Button>Ücretsiz Başla</Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="px-6 py-20 max-w-7xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 bg-white px-4 py-2 rounded-full text-sm text-primary font-medium mb-6">
          <Sparkles size={16} />
          AI-Powered Reklam Yönetimi
        </div>
        <h1 className="text-4xl md:text-6xl font-bold text-foreground max-w-4xl mx-auto leading-tight">
          Tüm reklam platformlarınızı{" "}
          <span className="text-primary">tek yerden</span>{" "}
          yönetin
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto">
          Google Ads, Meta Ads ve daha fazlasını birleştirin.
          AI destekli önerilerle performansınızı artırın.
          Günlük özet raporlarla her zaman bilgili kalın.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/register">
            <Button size="lg" className="text-lg px-8">
              Ücretsiz Dene
              <ArrowRight size={20} />
            </Button>
          </Link>
          <Link href="#features">
            <Button size="lg" variant="outline" className="text-lg px-8">
              Özellikleri Keşfet
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="mt-16 grid grid-cols-3 gap-8 max-w-3xl mx-auto">
          <div>
            <p className="text-4xl font-bold text-primary">₺2M+</p>
            <p className="text-sm text-muted-foreground mt-1">Optimize Edilen Bütçe</p>
          </div>
          <div>
            <p className="text-4xl font-bold text-primary">500+</p>
            <p className="text-sm text-muted-foreground mt-1">Aktif Hesap</p>
          </div>
          <div>
            <p className="text-4xl font-bold text-primary">%35</p>
            <p className="text-sm text-muted-foreground mt-1">Ortalama ROAS Artışı</p>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="px-6 py-20 bg-white">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">Neden AdWolf?</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={<BarChart3 className="text-primary" size={32} />}
              title="Unified Dashboard"
              description="Tüm reklam hesaplarınızı tek ekranda görün. Platform karşılaştırması yapın."
            />
            <FeatureCard
              icon={<Sparkles className="text-primary" size={32} />}
              title="AI-Powered Insights"
              description="GPT-4 ile otomatik analiz ve optimizasyon önerileri alın."
            />
            <FeatureCard
              icon={<Zap className="text-primary" size={32} />}
              title="Günlük Özet"
              description="Email veya WhatsApp ile günlük performans raporları alın."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 py-20 bg-primary">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-6">
            Hemen başlayın, ücretsiz deneyin
          </h2>
          <p className="text-primary-foreground/80 mb-8">
            Kredi kartı gerektirmez. 14 gün boyunca tüm özellikleri ücretsiz kullanın.
          </p>
          <Link href="/register">
            <Button size="lg" variant="secondary" className="text-lg px-8">
              Ücretsiz Hesap Oluştur
              <ArrowRight size={20} />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-8 bg-foreground text-white">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-white font-bold">A</span>
            </div>
            <span className="font-bold">AdWolf</span>
          </div>
          <p className="text-sm text-white/60">
            © 2024 AdWolf. Tüm hakları saklıdır.
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description
}: {
  icon: React.ReactNode;
  title: string;
  description: string
}) {
  return (
    <div className="p-6 rounded-xl border border-primary-light bg-cream-light hover:shadow-lg transition-shadow">
      <div className="w-14 h-14 rounded-lg bg-white flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}
