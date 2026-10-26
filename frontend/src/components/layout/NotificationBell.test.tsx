import { describe, expect, test, vi } from "vitest";
import { screen } from "@testing-library/react";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { renderWithProviders } from "@/test/utils";

const mocks = vi.hoisted(() => ({ unread: vi.fn() }));

vi.mock("@/hooks/useNotifications", () => ({
  useUnreadCount: () => mocks.unread(),
}));

describe("NotificationBell", () => {
  test("shows the unread count badge", () => {
    mocks.unread.mockReturnValue({ data: { unread: 5 } });
    renderWithProviders(<NotificationBell />);
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByLabelText("Notifications, 5 unread")).toBeInTheDocument();
  });

  test("shows no badge when there are no unread notifications", () => {
    mocks.unread.mockReturnValue({ data: { unread: 0 } });
    renderWithProviders(<NotificationBell />);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });
});
