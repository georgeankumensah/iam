"use server";

import { cookies } from "next/headers";
import { checkUserByLoginName, createSession, createCallback } from "@/lib/server/zitadel-client";
import { createSessionCookie } from "@/lib/server/session";
import { redirect } from "next/navigation";

export async function lookupUser(formData: FormData) {
  const loginName = formData.get("loginName") as string;
  const authRequest = formData.get("authRequest") as string;

  const { data: user, error } = await checkUserByLoginName(loginName);
  if (error || !user) {
    return { error: "User not found. Please check your email or username." };
  }

  return { userId: user.userId, loginName, authRequest };
}

export async function authenticateUser(formData: FormData) {
  const userId = formData.get("userId") as string;
  const password = formData.get("password") as string;
  const authRequest = formData.get("authRequest") as string;

  const { data: session, error: sessionError } = await createSession(userId, password);
  if (sessionError || !session) {
    return { error: "Failed to authenticate. Please try again." };
  }

  const cookie = createSessionCookie({
    id: session.sessionId,
    token: session.sessionToken,
    userId,
  });
  const cookieStore = await cookies();
  cookieStore.set(cookie.name, cookie.value, cookie.options);

  if (authRequest) {
    const { data: callback, error: cbError } = await createCallback(
      authRequest,
      session.sessionId,
      session.sessionToken
    );
    if (!cbError && callback?.callbackUrl) {
      redirect(callback.callbackUrl);
    }
  }

  redirect("/signedin");
}
