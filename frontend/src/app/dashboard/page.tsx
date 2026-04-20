"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuthStore } from "@/store/auth-store";
import { Shield } from "lucide-react";

// Check if user is admin (same logic as admin page)
function isAdminUser(user: { id: string; email: string } | null): boolean {
  if (!user) return false;
  return user.email.toLowerCase().includes("admin");
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const isAdmin = isAdminUser(user);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="text-2xl font-bold text-primary">
            LifePilot
          </Link>
          <div className="flex items-center gap-4">
            {isAdmin && (
              <Button asChild variant="outline" size="sm">
                <Link href="/admin" className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Admin
                </Link>
              </Button>
            )}
            <span className="text-sm text-muted-foreground">
              {user.email}
            </span>
            <Button variant="outline" size="sm" onClick={handleLogout}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">
            Welcome{user.firstName ? `, ${user.firstName}` : ""}!
          </h1>
          <p className="text-muted-foreground mt-2">
            Your life management dashboard
          </p>
        </div>

        {!user.phoneVerified && (
          <Card className="mb-8 border-yellow-200 bg-yellow-50">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-yellow-800">
                    Verify your phone number
                  </p>
                  <p className="text-sm text-yellow-700">
                    Add an extra layer of security to your account
                  </p>
                </div>
                <Button asChild size="sm">
                  <Link href="/auth/verify-phone">Verify now</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Profile completion prompt */}
        <Card className="mb-8 border-blue-200 bg-blue-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-blue-800">
                  Complete your profile
                </p>
                <p className="text-sm text-blue-700">
                  Add your academic and career details for personalized recommendations
                </p>
              </div>
              <Button asChild size="sm">
                <Link href="/profile">Complete Profile</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <DashboardCard
            title="Analytics"
            description="View your Life Score, badges, and weekly summaries"
            href="/dashboard/analytics"
            highlight
          />
          <DashboardCard
            title="Exam Feed"
            description="Discover relevant exams and track applications"
            href="/exams"
          />
          <DashboardCard
            title="Document Vault"
            description="Securely store and organize your documents"
            href="/documents"
          />
          <DashboardCard
            title="Money Manager"
            description="Track expenses and manage budgets"
            href="/money"
          />
          <DashboardCard
            title="Health Records"
            description="Store medical records and track vitals"
            href="/health"
          />
          <DashboardCard
            title="Wardrobe"
            description="Manage your clothes and get outfit suggestions"
            href="/wardrobe"
          />
          <DashboardCard
            title="Career Tracker"
            description="Track skills, courses, and job applications"
            href="/career"
          />
        </div>
      </main>
    </div>
  );
}

function DashboardCard({
  title,
  description,
  href,
  highlight,
}: {
  title: string;
  description: string;
  href: string;
  highlight?: boolean;
}) {
  return (
    <Card className={`hover:shadow-md transition-shadow ${highlight ? "border-primary bg-primary/5" : ""}`}>
      <Link href={href}>
        <CardHeader>
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <CardDescription>{description}</CardDescription>
        </CardContent>
      </Link>
    </Card>
  );
}
