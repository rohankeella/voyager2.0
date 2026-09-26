export default function DestinationLoading() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-7xl px-4 pt-24 pb-12 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <div className="h-4 w-48 animate-pulse rounded bg-gray-200" />
          <div className="flex gap-3">
            <div className="h-10 w-16 animate-pulse rounded-full bg-gray-200" />
            <div className="h-10 w-20 animate-pulse rounded-full bg-gray-200" />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-12 lg:grid-cols-3 lg:gap-12">
          <div className="lg:col-span-2">
            <div className="mb-8 space-y-3">
              <div className="h-10 w-3/4 animate-pulse rounded bg-gray-200" />
              <div className="h-6 w-1/2 animate-pulse rounded bg-gray-200" />
            </div>
            <div className="aspect-[4/3] animate-pulse rounded-2xl bg-gray-200" />
          </div>

          <div className="lg:col-span-1 space-y-6">
            <div className="h-[300px] w-full animate-pulse rounded-2xl bg-gray-200" />
            <div className="h-12 w-full animate-pulse rounded-full bg-gray-200" />
            <div className="h-12 w-full animate-pulse rounded-full bg-gray-200" />
          </div>
        </div>
      </div>
    </div>
  );
}
