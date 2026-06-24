import { redirect } from "next/navigation";

type Props = {
  searchParams: Promise<{ authRequest?: string }>;
};

export default async function LoginPage({ searchParams }: Props) {
  const { authRequest } = await searchParams;
  const params = new URLSearchParams();
  if (authRequest) params.set("authRequest", authRequest);
  const qs = params.toString();
  redirect(`/loginname${qs ? `?${qs}` : ""}`);
}
