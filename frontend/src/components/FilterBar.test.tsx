import { describe, expect, test, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { FilterBar } from "@/components/FilterBar";
import { renderWithProviders } from "@/test/utils";

describe("FilterBar", () => {
  test("debounces the search box and calls onChange", async () => {
    const onChange = vi.fn();
    renderWithProviders(<FilterBar value={{}} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Search tasks"), { target: { value: "report" } });
    expect(onChange).not.toHaveBeenCalled(); // debounced

    await waitFor(() =>
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ search: "report", page: 1 })),
    );
  });

  test("changing the status filter resets to page 1", () => {
    const onChange = vi.fn();
    renderWithProviders(<FilterBar value={{ page: 3 }} onChange={onChange} />);

    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "completed" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ status: "completed", page: 1 }));
  });

  test("renders project and assignee options", () => {
    renderWithProviders(
      <FilterBar
        value={{}}
        onChange={() => {}}
        projects={[{ id: "p1", name: "Alpha" } as never]}
        members={[{ user_id: "u1", full_name: "Jane", email: "j@x.com", role: "employee", status: "active", created_at: "" }]}
      />,
    );
    expect(screen.getByRole("option", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Jane" })).toBeInTheDocument();
  });
});
