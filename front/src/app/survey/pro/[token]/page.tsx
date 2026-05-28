"use client";

import { useParams } from "next/navigation";
import { SurveyForm } from "@/components/features/survey/SurveyForm";

export default function ProSurveyPage() {
  const { token } = useParams<{ token: string }>();

  if (!token) return null;

  return (
    <div className="min-h-screen bg-[#f4f1ea]">
      <SurveyForm token={token} />
    </div>
  );
}
