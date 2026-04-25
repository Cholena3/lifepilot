"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { authApi, ApiError } from "@/lib/api/auth";
import { useAuthStore } from "@/store/auth-store";

const phoneSchema = z.object({
  phone: z
    .string()
    .regex(/^\+?[1-9]\d{9,14}$/, "Please enter a valid phone number"),
});

type PhoneFormData = z.infer<typeof phoneSchema>;

export default function VerifyPhonePage() {
  const router = useRouter();
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const { user, setUser } = useAuthStore();

  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const [otpValues, setOtpValues] = useState(["", "", "", "", "", ""]);

  const phoneForm = useForm<PhoneFormData>({
    resolver: zodResolver(phoneSchema),
    defaultValues: {
      phone: "",
    },
  });

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const handleSendOTP = async (data: PhoneFormData) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await authApi.sendOTP({ phone: data.phone });
      setPhone(data.phone);
      setStep("otp");
      setCountdown(300); // 5 minutes
      
      // In dev mode, auto-fill the OTP
      if (response.dev_otp) {
        setDevOtp(response.dev_otp);
        const digits = response.dev_otp.split("");
        setOtpValues(digits);
        setSuccess(`OTP sent! (Dev mode — your code is: ${response.dev_otp})`);
      } else {
        setSuccess("OTP sent successfully! Check your phone.");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to send OTP. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async () => {
    const otp = otpValues.join("");
    if (otp.length !== 6) {
      setError("Please enter all 6 digits");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await authApi.verifyOTP({ phone, otp });
      
      // Update user state
      if (user) {
        setUser({ ...user, phoneVerified: true });
      }
      
      setSuccess("Phone verified successfully!");
      setTimeout(() => router.push("/dashboard"), 1500);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Invalid OTP. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendOTP = async () => {
    if (countdown > 0) return;
    
    setIsLoading(true);
    setError(null);

    try {
      const response = await authApi.sendOTP({ phone });
      setCountdown(300);
      if (response.dev_otp) {
        setDevOtp(response.dev_otp);
        const digits = response.dev_otp.split("");
        setOtpValues(digits);
        setSuccess(`OTP resent! (Dev mode — your code is: ${response.dev_otp})`);
      } else {
        setSuccess("OTP resent successfully!");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to resend OTP. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleOTPChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;

    const newValues = [...otpValues];
    newValues[index] = value.slice(-1);
    setOtpValues(newValues);

    // Auto-focus next input
    if (value && index < 5) {
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  const handleOTPKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === "Backspace" && !otpValues[index] && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
    }
  };

  const handleOTPPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").slice(0, 6);
    if (!/^\d+$/.test(pastedData)) return;

    const newValues = [...otpValues];
    for (let i = 0; i < pastedData.length; i++) {
      newValues[i] = pastedData[i];
    }
    setOtpValues(newValues);

    // Focus the next empty input or the last one
    const nextEmptyIndex = newValues.findIndex((v) => !v);
    const focusIndex = nextEmptyIndex === -1 ? 5 : nextEmptyIndex;
    otpInputRefs.current[focusIndex]?.focus();
  };

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl text-center">
          {step === "phone" ? "Verify Your Phone" : "Enter OTP"}
        </CardTitle>
        <CardDescription className="text-center">
          {step === "phone"
            ? "We'll send you a 6-digit code to verify your phone number"
            : `Enter the code sent to ${phone}`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 text-sm text-red-500 bg-red-50 border border-red-200 rounded-md">
            {error}
          </div>
        )}

        {success && (
          <div className="p-3 text-sm text-green-600 bg-green-50 border border-green-200 rounded-md">
            {success}
          </div>
        )}

        {step === "phone" ? (
          <Form {...phoneForm}>
            <form
              onSubmit={phoneForm.handleSubmit(handleSendOTP)}
              className="space-y-4"
            >
              <FormField
                control={phoneForm.control}
                name="phone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Phone Number</FormLabel>
                    <FormControl>
                      <Input
                        type="tel"
                        placeholder="+1234567890"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Sending..." : "Send OTP"}
              </Button>
            </form>
          </Form>
        ) : (
          <div className="space-y-4">
            <div className="flex justify-center gap-2" onPaste={handleOTPPaste}>
              {otpValues.map((value, index) => (
                <Input
                  key={index}
                  ref={(el) => {
                    otpInputRefs.current[index] = el;
                  }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={value}
                  onChange={(e) => handleOTPChange(index, e.target.value)}
                  onKeyDown={(e) => handleOTPKeyDown(index, e)}
                  className="w-12 h-12 text-center text-lg font-semibold"
                />
              ))}
            </div>

            <Button
              onClick={handleVerifyOTP}
              className="w-full"
              disabled={isLoading || otpValues.some((v) => !v)}
            >
              {isLoading ? "Verifying..." : "Verify OTP"}
            </Button>

            <div className="text-center space-y-2">
              {countdown > 0 ? (
                <p className="text-sm text-muted-foreground">
                  Code expires in {formatCountdown(countdown)}
                </p>
              ) : (
                <p className="text-sm text-red-500">Code expired</p>
              )}

              <Button
                variant="link"
                onClick={handleResendOTP}
                disabled={countdown > 0 || isLoading}
                className="text-sm"
              >
                {countdown > 0
                  ? `Resend in ${formatCountdown(countdown)}`
                  : "Resend OTP"}
              </Button>

              <Button
                variant="link"
                onClick={() => {
                  setStep("phone");
                  setOtpValues(["", "", "", "", "", ""]);
                  setError(null);
                  setSuccess(null);
                }}
                className="text-sm"
              >
                Change phone number
              </Button>
            </div>
          </div>
        )}

        <div className="text-center">
          <Button
            variant="ghost"
            onClick={() => router.push("/dashboard")}
            className="text-sm text-muted-foreground"
          >
            Skip for now
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
