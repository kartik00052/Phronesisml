import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";

import { queryClient } from "@/lib/query-client";
import { AppShell } from "@/components/layout/app-shell";
import { ErrorBoundary } from "@/components/layout/error-boundary";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import { PageSkeleton } from "@/components/layout/page-skeleton";

const DashboardPage = lazy(() => import("@/pages/dashboard"));
const RunsListPage = lazy(() => import("@/pages/runs/index"));
const RunComparePage = lazy(() => import("@/pages/runs/compare"));
const NewRunPage = lazy(() => import("@/pages/runs/new"));
const RunLayout = lazy(() => import("@/pages/runs/[id]/layout"));
const RunOverviewTab = lazy(() => import("@/pages/runs/[id]/index"));
const RunPipelineTab = lazy(() => import("@/pages/runs/[id]/pipeline"));
const RunDataTab = lazy(() => import("@/pages/runs/[id]/data"));
const RunModelsTab = lazy(() => import("@/pages/runs/[id]/models"));
const RunExplainabilityTab = lazy(() => import("@/pages/runs/[id]/explainability"));
const RunReportsTab = lazy(() => import("@/pages/runs/[id]/reports"));
const RunArtifactsTab = lazy(() => import("@/pages/runs/[id]/artifacts"));
const RunLogsTab = lazy(() => import("@/pages/runs/[id]/logs"));
const DatasetsPage = lazy(() => import("@/pages/datasets"));
const ModelsPage = lazy(() => import("@/pages/models"));
const ExplainabilityPage = lazy(() => import("@/pages/explainability"));
const ReportsPage = lazy(() => import("@/pages/reports"));
const ArtifactsPage = lazy(() => import("@/pages/artifacts"));
const SettingsPage = lazy(() => import("@/pages/settings"));
const NotFoundPage = lazy(() => import("@/pages/not-found"));

function lazyPage(Component: React.LazyExoticComponent<() => React.ReactNode>) {
  return <Component />;
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Suspense fallback={<PageSkeleton />}>{lazyPage(DashboardPage)}</Suspense>,
      },
      {
        path: "runs",
        children: [
          { index: true, element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunsListPage)}</Suspense> },
          { path: "new", element: <Suspense fallback={<PageSkeleton />}>{lazyPage(NewRunPage)}</Suspense> },
          {
            path: "compare",
            element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunComparePage)}</Suspense>,
          },
          {
            path: ":runId",
            element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunLayout)}</Suspense>,
            children: [
              {
                index: true,
                element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunOverviewTab)}</Suspense>,
              },
              {
                path: "pipeline",
                element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunPipelineTab)}</Suspense>,
              },
              {
                path: "data",
                element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunDataTab)}</Suspense>,
              },
              {
                path: "models",
                element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunModelsTab)}</Suspense>,
              },
              {
                path: "explainability",
                element: (
                  <Suspense fallback={<PageSkeleton />}>{lazyPage(RunExplainabilityTab)}</Suspense>
                ),
              },
              {
                path: "reports",
                element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunReportsTab)}</Suspense>,
              },
              {
                path: "artifacts",
                element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunArtifactsTab)}</Suspense>,
              },
              {
                path: "logs",
                element: <Suspense fallback={<PageSkeleton />}>{lazyPage(RunLogsTab)}</Suspense>,
              },
            ],
          },
        ],
      },
      { path: "datasets", element: <Suspense fallback={<PageSkeleton />}>{lazyPage(DatasetsPage)}</Suspense> },
      { path: "models", element: <Suspense fallback={<PageSkeleton />}>{lazyPage(ModelsPage)}</Suspense> },
      {
        path: "explainability",
        element: <Suspense fallback={<PageSkeleton />}>{lazyPage(ExplainabilityPage)}</Suspense>,
      },
      { path: "reports", element: <Suspense fallback={<PageSkeleton />}>{lazyPage(ReportsPage)}</Suspense> },
      { path: "artifacts", element: <Suspense fallback={<PageSkeleton />}>{lazyPage(ArtifactsPage)}</Suspense> },
      { path: "settings", element: <Suspense fallback={<PageSkeleton />}>{lazyPage(SettingsPage)}</Suspense> },
      { path: "*", element: <Suspense fallback={<PageSkeleton />}>{lazyPage(NotFoundPage)}</Suspense> },
    ],
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={200}>
        <ErrorBoundary>
          <RouterProvider router={router} />
          <Toaster />
        </ErrorBoundary>
      </TooltipProvider>
    </QueryClientProvider>
  );
}