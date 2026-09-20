import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/ui/data-table";

interface Row {
  name: string;
  score: number;
}

const columns: ColumnDef<Row, unknown>[] = [
  { id: "name", accessorKey: "name", header: "Name" },
  { id: "score", accessorKey: "score", header: "Score" },
];

const rows: Row[] = [
  { name: "random_forest", score: 0.91 },
  { name: "logistic_regression", score: 0.83 },
  { name: "gradient_boosting", score: 0.95 },
];

describe("DataTable", () => {
  it("renders rows and a row count", () => {
    render(<DataTable columns={columns} data={rows} />);
    expect(screen.getByText("random_forest")).toBeInTheDocument();
    expect(screen.getByText("3 rows")).toBeInTheDocument();
  });

  it("filters rows from the search box", () => {
    render(<DataTable columns={columns} data={rows} />);
    fireEvent.change(screen.getByLabelText("Search table"), {
      target: { value: "boosting" },
    });
    expect(screen.getByText("gradient_boosting")).toBeInTheDocument();
    expect(screen.queryByText("random_forest")).not.toBeInTheDocument();
  });

  it("sorts rows when a sortable header is activated", () => {
    render(<DataTable columns={columns} data={rows} initialSorting={[{ id: "score", desc: false }]} />);
    const body = screen.getAllByRole("rowgroup")[1];
    const firstDataRow = within(body).getAllByRole("row")[0];
    expect(within(firstDataRow).getByText("logistic_regression")).toBeInTheDocument();
  });

  it("shows an empty state when there is no data", () => {
    render(
      <DataTable
        columns={columns}
        data={[]}
        emptyMessage="Nothing here"
        emptyHint="Try another filter"
      />,
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Try another filter")).toBeInTheDocument();
  });

  it("invokes onRowClick with the clicked row", () => {
    const onClick = vi.fn();
    render(<DataTable columns={columns} data={rows} onRowClick={onClick} />);
    fireEvent.click(screen.getByText("random_forest"));
    expect(onClick).toHaveBeenCalledWith(rows[0]);
  });

  it("renders skeleton rows while loading", () => {
    render(<DataTable columns={columns} data={[]} loading />);
    expect(screen.queryByText("Nothing here")).not.toBeInTheDocument();
  });
});
