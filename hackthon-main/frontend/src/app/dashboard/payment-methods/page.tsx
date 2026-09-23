import { CreditCard } from "lucide-react";
import ComingSoon from "@/components/dashboard/coming-soon";

export default function PaymentMethodsPage() {
  return (
    <ComingSoon
      icon={CreditCard}
      title="Payment Methods"
      description="Saved cards and payment preferences for faster checkout when booking a trip."
    />
  );
}
