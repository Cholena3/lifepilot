import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-muted">
      <div className="container mx-auto px-4 py-16">
        <div className="flex flex-col items-center text-center space-y-8">
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            Welcome to <span className="text-primary">LifePilot</span>
          </h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            Your comprehensive life management platform. Manage exams,
            documents, finances, health records, wardrobe, and career
            progression all in one place.
          </p>
          <div className="flex gap-4">
            <Button asChild size="lg">
              <Link href="/auth/login">Get Started</Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/auth/register">Create Account</Link>
            </Button>
          </div>
        </div>

        <div className="mt-24 grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          <FeatureCard
            title="Exam Management"
            description="Discover relevant exams, track applications, and sync with your calendar."
          />
          <FeatureCard
            title="Document Vault"
            description="Securely store and organize your important documents with OCR support."
          />
          <FeatureCard
            title="Money Manager"
            description="Track expenses, set budgets, and split bills with friends."
          />
          <FeatureCard
            title="Health Records"
            description="Store medical records, track medicines, and monitor vitals."
          />
          <FeatureCard
            title="Wardrobe Manager"
            description="Catalog your clothes and get daily outfit suggestions."
          />
          <FeatureCard
            title="Career Tracker"
            description="Track skills, courses, job applications, and build your resume."
          />
        </div>
      </div>
    </main>
  );
}

function FeatureCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription>{description}</CardDescription>
      </CardContent>
    </Card>
  );
}
