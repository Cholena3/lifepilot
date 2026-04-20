"use client";

import { Suspense } from "react";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authApi, ApiError } from "@/lib/api/auth";
import { useAuthStore } from "@/store/auth-store";

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const { setTokens, setUser } = useAuthStore();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError("Authentication was cancelled or failed. Please try again.");
        return;
      }

      if (!code) {
        setError("No authorization code received. Please try again.");
        return;
      }

      try {
        const tokens = await authApi.googleCallback(code);
        setTokens(tokens.access_token, tokens.refresh_token);

        // Fetch user data
        const user = await authApi.getCurrentUser();
        setUser({
          id: user.id,
          email: user.email,
          firstName: user.first_name,
          lastName: user.last_name,
          avatarUrl: user.avatar_url,
          phoneVerified: user.phone_verified,
        });

        router.push("/dashboard");
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("An unexpected error occurred. Please try again.");
        }
      }
    };

    handleCallback();
  }, [searchParams, router, setTokens, setUser]);

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-center text-red-500">
            Authentication Failed
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-muted-foreground">{error}</p>
          <a href="/auth/login" className="text-primary hover:underline">
            Return to login
          </a>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center">Completing sign in...</CardTitle>
      </CardHeader>
      <CardContent className="flex justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </CardContent>
    </Card>
  );
}

function LoadingFallback() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-center">Loading...</CardTitle>
      </CardHeader>
      <CardContent className="flex justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </CardContent>
    </Card>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <OAuthCallbackContent />
    </Suspense>
  );
}
