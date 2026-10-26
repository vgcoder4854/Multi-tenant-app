import { describe, expect, test, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Login } from "@/pages/Login";
import { ApiError } from "@/api/client";
import { makeAuth, renderWithProviders } from "@/test/utils";

describe("Login page", () => {
  test("shows client-side validation errors", async () => {
    const user = userEvent.setup();
    renderWithProviders(<Login />, { route: "/login" });

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
  });

  test("shows the server error returned by the API", async () => {
    const user = userEvent.setup();
    const login = vi.fn().mockRejectedValue(new ApiError(401, "INVALID_CREDENTIALS", "Invalid email or password"));
    renderWithProviders(<Login />, { route: "/login", auth: makeAuth({ login }) });

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "wrongpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(login).toHaveBeenCalledWith("user@example.com", "wrongpass"));
    expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
  });
});
