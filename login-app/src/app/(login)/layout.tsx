export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">CLET IAM</h1>
          <p className="mt-2 text-sm text-gray-600">
            Centralised Identity & Access Management
          </p>
        </div>
        {children}
      </div>
    </div>
  );
}
