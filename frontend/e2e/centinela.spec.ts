import { expect, test } from "@playwright/test";

test("admin can register and inspect a monitored service", async ({ page }) => {
  const serviceName = `E2E service ${Date.now()}`;
  await page.goto("/");
  await page.getByLabel("Clave administrativa").fill("e2e-key");
  await page.getByRole("button", { name: "Entrar a Centinela" }).click();
  await expect(page.getByRole("heading", { name: "Tu sistema, de un vistazo" })).toBeVisible();

  await page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name: "Servicios" }).click();
  await page.getByRole("button", { name: "Nuevo servicio" }).click();
  await page.getByLabel("Nombre", { exact: true }).fill(serviceName);
  await page.getByLabel("URL de salud", { exact: true }).fill("http://127.0.0.1:8000/health");
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByText(serviceName)).toBeVisible();

  await page.getByRole("link", { name: serviceName }).click();
  await page.getByRole("button", { name: "Ejecutar chequeo" }).click();
  await expect(page.getByText("Operativo").first()).toBeVisible();

  await page.route("**/api/v1/ai/config/test", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, provider: "openai", model: "test-model", latency_ms: 14 }),
    });
  });
  await page
    .getByRole("navigation", { name: "Principal" })
    .getByRole("link", { name: "Inteligencia IA" })
    .click();
  await page.getByRole("button", { name: /OpenAI/ }).click();
  await page.getByLabel("Modelo").fill("test-model");
  await page.getByLabel("Clave de API").fill("sk-e2e-provider-key");
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await page.getByRole("button", { name: "Probar conexión" }).click();
  await expect(page.getByText("Conexión correcta · 14 ms")).toBeVisible();
});
