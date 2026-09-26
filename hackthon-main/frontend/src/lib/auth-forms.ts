import { countries } from "@/lib/mock-data";

export type UserFormData = {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
  country: string;
  phone: string;
  agreedToTerms: boolean;
};

export type FormErrors = Partial<Record<keyof UserFormData, string>>;

export function validateUserForm(values: UserFormData): FormErrors {
  const errors: FormErrors = {};

  if (!values.fullName.trim()) {
    errors.fullName = "Full name is required";
  } else if (values.fullName.trim().length < 2) {
    errors.fullName = "Name is too short";
  }

  if (!values.email.trim()) {
    errors.email = "Email is required";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
    errors.email = "Enter a valid email address";
  }

  if (!values.password) {
    errors.password = "Password is required";
  } else if (values.password.length < 6) {
    errors.password = "Password must be at least 6 characters";
  }

  if (!values.confirmPassword) {
    errors.confirmPassword = "Please confirm your password";
  } else if (values.confirmPassword !== values.password) {
    errors.confirmPassword = "Passwords do not match";
  }

  if (!values.country) {
    errors.country = "Please select a country";
  }

  if (values.phone && !/^\+?[0-9\s-]{7,15}$/.test(values.phone)) {
    errors.phone = "Enter a valid phone number";
  }

  if (!values.agreedToTerms) {
    errors.agreedToTerms = "You must agree to the Terms & Privacy Policy";
  }

  return errors;
}

export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  if (!password) return { score: 0, label: "", color: "bg-gray-200" };

  let score = 0;
  if (password.length >= 6) score += 1;
  if (password.length >= 10) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (score <= 1) return { score, label: "Weak", color: "bg-red-500" };
  if (score === 2) return { score, label: "Fair", color: "bg-orange-400" };
  if (score === 3) return { score, label: "Good", color: "bg-yellow-400" };
  if (score === 4) return { score, label: "Strong", color: "bg-green-500" };
  return { score, label: "Very strong", color: "bg-emerald-600" };
}

export { countries };
