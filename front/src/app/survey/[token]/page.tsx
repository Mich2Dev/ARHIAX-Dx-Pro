import { SurveyForm } from "@/components/features/survey/SurveyForm";

export default function SurveyPage({ params }: { params: { token: string } }) {
  return <SurveyForm token={params.token} />;
}
