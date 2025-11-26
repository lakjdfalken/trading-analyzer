import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="flex flex-col items-center gap-4 text-center max-w-md p-6">
        <div className="text-6xl font-bold text-muted-foreground">404</div>
        <div>
          <h2 className="text-xl font-semibold">Page Not Found</h2>
          <p className="text-muted-foreground mt-2">
            The page you are looking for does not exist or has been moved.
          </p>
        </div>
        <Link
          href="/"
          className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
