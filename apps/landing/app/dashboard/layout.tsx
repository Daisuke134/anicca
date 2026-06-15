import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Anicca Dashboard — Lineage + Live Numbers",
  description:
    "全 Anicca 個体 (lineage) のリアルタイム指標。各個体の収支/lifeline/wallet 残高を公開。",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
