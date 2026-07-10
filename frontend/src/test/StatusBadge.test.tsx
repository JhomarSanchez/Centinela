import { act, render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";

import { StatusBadge } from "../components/StatusBadge";
import i18n from "../i18n";

test("status is conveyed with readable text, not color alone", () => {
  render(<I18nextProvider i18n={i18n}><StatusBadge status="down" /></I18nextProvider>);
  expect(screen.getByText("Caído")).toBeInTheDocument();
});

test("the same status is available in English", async () => {
  await act(async () => i18n.changeLanguage("en"));
  render(<I18nextProvider i18n={i18n}><StatusBadge status="down" /></I18nextProvider>);
  expect(screen.getByText("Down")).toBeInTheDocument();
  await act(async () => i18n.changeLanguage("es"));
});
