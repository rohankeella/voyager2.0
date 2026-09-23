"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { validateUserForm, getPasswordStrength, type UserFormData } from "@/lib/auth-forms";
import { countries } from "@/lib/mock-data";
import { cn } from "@/lib/utils";
import { ApiError, authApi, setSession } from "@/lib/api";

const initialFormData: UserFormData = {
  fullName: "",
  email: "",
  password: "",
  confirmPassword: "",
  country: "",
  phone: "",
  agreedToTerms: false,
};

export default function RegisterPage() {
  const [formData, setFormData] = useState<UserFormData>(initialFormData);
  const [errors, setErrors] = useState<Partial<Record<keyof UserFormData, string>>>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const passwordStrength = getPasswordStrength(formData.password);

  const handleChange = (field: keyof UserFormData) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const value = e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value;
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
    setSubmitError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError("");
    const validationErrors = validateUserForm(formData);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await authApi.register({
        email: formData.email,
        password: formData.password,
        full_name: formData.fullName,
        country: formData.country || undefined,
        phone: formData.phone || undefined,
      });
      setSession(res);
      setSubmitSuccess(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setSubmitError("An account with that email already exists.");
      } else if (err instanceof ApiError) {
        setSubmitError(err.message);
      } else {
        setSubmitError("Couldn't reach the server. Is the backend running?");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <div className="hidden lg:flex lg:w-1/2 relative">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?ixlib=rb-4.0.3&auto=format&fit=crop&w=2073&q=80')",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-dark/80 via-primary/60 to-dark/90" />
        <div className="relative z-10 flex flex-col justify-end p-12 text-white">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8 }}
          >
            <blockquote className="text-2xl font-medium leading-relaxed">
              "The world is a book, and those who do not travel read only one page."
            </blockquote>
            <p className="mt-4 text-sm text-white/70">— Saint Augustine</p>
            <div className="mt-8 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-xs backdrop-blur-md">
              <span className="h-2 w-2 rounded-full bg-secondary" />
              Santorini, Greece
            </div>
          </motion.div>
        </div>
      </div>

      <div className="flex w-full lg:w-1/2 items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md"
        >
          <div className="mb-8">
            <Link href="/" className="inline-flex items-center gap-2 text-xl font-bold text-dark">
              Voyager
            </Link>
            <h1 className="mt-6 text-3xl font-bold tracking-tight text-dark">Create your account</h1>
            <p className="mt-2 text-sm text-gray-600">
              Already have an account?{" "}
              <Link href="/login" className="font-semibold text-primary hover:text-primary/80">
                Log in
              </Link>
            </p>
          </div>

          <AnimatePresence mode="wait">
            {submitSuccess ? (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="rounded-2xl border border-green-100 bg-green-50 p-8 text-center"
              >
                <CheckCircle2 className="mx-auto h-12 w-12 text-green-600" />
                <h2 className="mt-4 text-xl font-semibold text-green-900">Account created!</h2>
                <p className="mt-2 text-sm text-green-700">
                  Welcome aboard. Let&apos;s personalize your travel experience.
                </p>
                <Link
                  href="/onboarding"
                  className="mt-6 inline-flex rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
                >
                  Start Onboarding
                </Link>
              </motion.div>
            ) : (
              <motion.form
                key="form"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                onSubmit={handleSubmit}
                className="space-y-5"
              >
                <AnimatePresence>
                  {submitError && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="flex items-center gap-2 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700"
                    >
                      <AlertCircle className="h-4 w-4" />
                      {submitError}
                    </motion.div>
                  )}
                </AnimatePresence>

                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium text-dark">
                    Full name
                  </label>
                  <input
                    id="fullName"
                    type="text"
                    value={formData.fullName}
                    onChange={handleChange("fullName")}
                    className={cn(
                      "mt-1.5 block w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20",
                      errors.fullName ? "border-red-400" : "border-gray-200"
                    )}
                    placeholder="John Doe"
                  />
                  <AnimatePresence>
                    {errors.fullName && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-1.5 text-xs text-red-600"
                      >
                        {errors.fullName}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-dark">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange("email")}
                    className={cn(
                      "mt-1.5 block w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20",
                      errors.email ? "border-red-400" : "border-gray-200"
                    )}
                    placeholder="you@example.com"
                  />
                  <AnimatePresence>
                    {errors.email && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-1.5 text-xs text-red-600"
                      >
                        {errors.email}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-dark">
                    Password
                  </label>
                  <div className="relative mt-1.5">
                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={formData.password}
                      onChange={handleChange("password")}
                      className={cn(
                        "block w-full rounded-xl border bg-white px-3.5 py-2.5 pr-10 text-sm shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20",
                        errors.password ? "border-red-400" : "border-gray-200"
                      )}
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <AnimatePresence>
                    {errors.password && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-1.5 text-xs text-red-600"
                      >
                        {errors.password}
                      </motion.p>
                    )}
                  </AnimatePresence>
                  {formData.password && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="mt-2"
                    >
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 flex-1 rounded-full bg-gray-200">
                          <div
                            className={cn("h-full rounded-full transition-all", passwordStrength.color)}
                            style={{ width: `${(passwordStrength.score / 5) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500">{passwordStrength.label}</span>
                      </div>
                    </motion.div>
                  )}
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-dark">
                    Confirm password
                  </label>
                  <div className="relative mt-1.5">
                    <input
                      id="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      value={formData.confirmPassword}
                      onChange={handleChange("confirmPassword")}
                      className={cn(
                        "block w-full rounded-xl border bg-white px-3.5 py-2.5 pr-10 text-sm shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20",
                        errors.confirmPassword ? "border-red-400" : "border-gray-200"
                      )}
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((prev) => !prev)}
                      className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <AnimatePresence>
                    {errors.confirmPassword && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-1.5 text-xs text-red-600"
                      >
                        {errors.confirmPassword}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                <div>
                  <label htmlFor="country" className="block text-sm font-medium text-dark">
                    Country
                  </label>
                  <select
                    id="country"
                    value={formData.country}
                    onChange={handleChange("country")}
                    className={cn(
                      "mt-1.5 block w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20",
                      errors.country ? "border-red-400" : "border-gray-200"
                    )}
                  >
                    <option value="">Select a country</option>
                    {countries.map((country) => (
                      <option key={country.code} value={country.name}>
                        {country.name}
                      </option>
                    ))}
                  </select>
                  <AnimatePresence>
                    {errors.country && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-1.5 text-xs text-red-600"
                      >
                        {errors.country}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                <div>
                  <label htmlFor="phone" className="block text-sm font-medium text-dark">
                    Phone number{" "}
                    <span className="font-normal text-gray-500">(optional)</span>
                  </label>
                  <input
                    id="phone"
                    type="tel"
                    value={formData.phone}
                    onChange={handleChange("phone")}
                    className={cn(
                      "mt-1.5 block w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20",
                      errors.phone ? "border-red-400" : "border-gray-200"
                    )}
                    placeholder="+1 (555) 000-0000"
                  />
                  <AnimatePresence>
                    {errors.phone && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-1.5 text-xs text-red-600"
                      >
                        {errors.phone}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                <div>
                  <label className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={formData.agreedToTerms}
                      onChange={handleChange("agreedToTerms")}
                      className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                    <span className="text-sm text-gray-600">
                      I agree to the{" "}
                      <Link href="#" className="text-primary hover:text-primary/80">
                        Terms & Privacy Policy
                      </Link>
                    </span>
                  </label>
                  <AnimatePresence>
                    {errors.agreedToTerms && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-1.5 text-xs text-red-600"
                      >
                        {errors.agreedToTerms}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex w-full items-center justify-center rounded-full bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 disabled:opacity-70"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating account...
                    </>
                  ) : (
                    "Create Account"
                  )}
                </button>
              </motion.form>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  );
}
