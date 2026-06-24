"use server";

import { cookies } from "next/headers";
import { checkUserByLoginName, verifyPassword, createSession, getAuthRequest, createCallback } from "@/lib/server/zitadel-client";
import { createSessionCookie } from "@/lib/server/session";
import { redirect } from "next/navigation";

export async function lookupUser(formData: FormData) {
  const loginName = formData.get("loginName") as string;
  const authRequest = formData.get("authRequest") as string;

  const { data: user, error } = await checkUserByLoginName(loginName);
  if (error || !user) {
    return { error: "User not found. Please check your email or username." };
  }

  return {
    userId: user.userId,
    loginName,
    authRequest,
  };
}

export async function authenticateUser(formData: FormData) {
  const userId = formData.get("userId") as string;
  const password = formData.get("password") as string;
  const authRequest = formData.get("authRequest") as string;

  const { data: verified, error: verifyError } = await verifyPassword(userId, password);
  if (verifyError || !verified?.verified) {
    return { error: "Invalid password. Please try again." };
  }

  const { data: session, error: sessionError } = await createSession(userId, { password: { password } });
  if (sessionError || !session) {
    return { error: "Failed to create session. Please try again." };
  }

  const cookie = createSessionCookie({ id: session.sessionId, token: session.token, userId });
  const cookieStore = await cookies();
  cookieStore.set(cookie.name, cookie.value, cookie.options);

  if (authRequest) {
    const { data: authReq, error: authError } = await getAuthRequest(authRequest);
    if (!authError && authReq) {
      const { data: callback, error: cbError } = await createCallback(authRequest, session.sessionId);
      if (!cbError && callback?.callbackUrl) {
        redirect(callback.callbackUrl);
      }
    }
  }

  redirect("/signedin");
}
