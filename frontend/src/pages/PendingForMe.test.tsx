import { beforeEach, describe, expect, test, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/api/client";
import { PendingForMe } from "@/pages/PendingForMe";
import { renderWithProviders } from "@/test/utils";

const mocks = vi.hoisted(() => ({ pending: vi.fn(), decide: vi.fn() }));

vi.mock("@/hooks/useWorkflows", () => ({
  usePendingForMe: () => mocks.pending(),
  useDecideRequest: () => ({ mutateAsync: mocks.decide, isPending: false }),
}));

const REQUEST = {
  id: "req-1",
  org_id: "org-1",
  template_id: "tpl-1",
  template_name: "Leave Approval",
  requester_id: "user-2",
  requester_name: "Someone Else",
  title: "Vacation",
  details: {},
  status: "pending" as const,
  current_step_order: 1,
  submitted_at: new Date().toISOString(),
  completed_at: null,
};

describe("PendingForMe", () => {
  beforeEach(() => {
    mocks.pending.mockReturnValue({ data: [REQUEST], isLoading: false, error: null });
    mocks.decide.mockReset();
  });

  test("approving calls the decision API with 'approved'", async () => {
    mocks.decide.mockResolvedValue({});
    const user = userEvent.setup();
    renderWithProviders(<PendingForMe />, { route: "/requests/pending" });

    await user.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(mocks.decide).toHaveBeenCalledWith({ decision: "approved", comment: undefined }));
  });

  test("rejecting requires a comment before calling the API", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PendingForMe />, { route: "/requests/pending" });

    await user.click(screen.getByRole("button", { name: "Reject" }));
    expect(mocks.decide).not.toHaveBeenCalled();
    expect(await screen.findByText("A comment is required when rejecting")).toBeInTheDocument();
  });

  test("shows a clear message when the request was already decided (409)", async () => {
    mocks.decide.mockRejectedValue(new ApiError(409, "REQUEST_NOT_PENDING", "This request has already been decided"));
    const user = userEvent.setup();
    renderWithProviders(<PendingForMe />, { route: "/requests/pending" });

    await user.click(screen.getByRole("button", { name: "Approve" }));

    expect(await screen.findByText("This request has already been decided")).toBeInTheDocument();
    expect(await screen.findByText(/Already decided/i)).toBeInTheDocument();
  });
});
