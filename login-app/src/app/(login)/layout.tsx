export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#fbfcfd] px-5 py-8 text-[#101010]">
      <div className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center overflow-hidden">
        <img
          src="/iam-assets/images/gsl.png"
          alt=""
          aria-hidden="true"
          className="max-w-none select-none opacity-[0.56] blur-[7px] w-[880px] sm:w-[980px] lg:w-[1060px] xl:w-[1120px]"
        />
      </div>

      <section className="relative z-10 flex min-h-[calc(100vh-64px)] items-center justify-center">
        <div className="w-full max-w-[560px]">
          <div className="mb-4 text-center">
            <img
              src="/iam-assets/images/gsl-logo.svg"
              alt="Ghana School of Law"
              className="mx-auto h-[72px] w-auto object-contain"
            />
          </div>
          {children}
          <div className="mt-7 text-center text-[12px] text-[#161616]">
            <p>Need help? Contact the System Administrator</p>
            <div className="mt-3 flex items-center justify-center gap-2 text-[#555]">
              <a href="#" className="hover:underline">Security Notice</a>
              <a href="#" className="hover:underline">Accessibility</a>
              <a href="#" className="hover:underline">Privacy Policy</a>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
