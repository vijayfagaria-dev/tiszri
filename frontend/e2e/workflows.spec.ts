import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("overview to replay, selection, filters and history", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /How far/ })).toBeVisible();
  await expect(page).toHaveURL(/rule=d1-0900/);
  await page.getByRole("button", { name: "Ranked", exact: true }).click();
  await expect(page.getByText("Highest MAE first")).toBeVisible();
  await page.getByRole("link", { name: /Worst day/ }).click();
  await expect(
    page.getByRole("heading", { name: "Forecast vs actual" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Select interval 24, vintage", exact: false })
    .click();
  await expect(page).toHaveURL(/interval=24/);
  await expect(page.locator("#interval-inspector")).toContainText(
    "Interval 24",
  );
  await page
    .getByRole("button", { name: "Inspect interval 10", exact: true })
    .click();
  await expect(page).toHaveURL(/interval=10/);
  await page.goBack();
  await expect(page).toHaveURL(/interval=24/);
  await expect(page.getByRole("slider")).toHaveValue("24");
});
test("partial, empty, all-status and hindsight evidence", async ({ page }) => {
  await page.goto("/replay?date=2026-01-15&rule=d2-0900");
  await expect(page.getByText(/Partial evidence —/)).toBeVisible();
  await page
    .getByRole("button", { name: "Not published 4", exact: true })
    .click();
  await expect(page.locator("tbody tr")).toHaveCount(4);
  await page.getByLabel("Demo scenario").selectOption("empty");
  await expect(
    page.getByRole("heading", {
      name: "No matched evidence at this decision time",
    }),
  ).toBeVisible();
  await expect(page.locator(".metric-value").first()).toHaveText("Unavailable");
  await page.getByLabel("Demo scenario").selectOption("edge");
  await page.getByLabel("Forecast decision time").selectOption("d1-0900");
  await page.getByRole("button", { name: "All 48", exact: true }).click();
  await expect(page.locator("tbody")).toContainText("Ambiguous forecast");
  await page.getByLabel("Forecast decision time").selectOption("after-0000");
  await expect(page.getByText("Hindsight view", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Switch to Morning before" }).click();
  await expect(page).toHaveURL(/rule=d1-0900/);
});
test("errors are recoverable and malformed responses are not rendered", async ({
  page,
}) => {
  await page.goto("/?mockError=malformed");
  await expect(page.getByRole("alert")).toContainText("doesn’t recognise");
  await page.getByLabel("Demo scenario").selectOption("complete");
  await expect(page.getByRole("heading", { name: /How far/ })).toBeVisible();
});
test("a slower prior request cannot replace the new decision", async ({
  page,
}) => {
  await page.goto("/replay?date=2026-01-16&rule=d1-0900&mockDelay=1400");
  await expect(page.getByLabel("Forecast decision time")).toBeVisible();
  await page.getByLabel("Forecast decision time").selectOption("d1-1200");
  await expect(page.locator(".replay-heading")).toContainText("12:00 GMT");
  await page.waitForTimeout(1600);
  await expect(page.locator(".replay-heading")).toContainText("12:00 GMT");
});
test("offline notice is persistent and reconnect restores access", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /How far/ })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByRole("alert")).toContainText("offline");
  await context.setOffline(false);
  await expect(page.locator(".offline")).toHaveCount(0);
});
for (const route of ["/", "/replay?date=2026-01-16&rule=d1-0900"])
  test(`responsive and accessible ${route}`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator(".metric-value").first()).toBeVisible();
    const scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(
      scan.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes
          .slice(0, 3)
          .map((n) => ({ target: n.target, reason: n.failureSummary })),
      })),
    ).toEqual([]);
    for (const width of [320, 720, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      const overflow = await page.evaluate(() => ({
        width: innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        elements: [...document.querySelectorAll("main *")]
          .filter(
            (el) =>
              el.getBoundingClientRect().right > innerWidth &&
              !el.closest(".table-scroll,.vintage-ribbon,.error-fingerprint"),
          )
          .slice(0, 10)
          .map((el) => ({
            tag: el.tagName,
            class: el.className,
            right: el.getBoundingClientRect().right,
          })),
      }));
      expect(
        overflow.documentWidth,
        JSON.stringify(overflow),
      ).toBeLessThanOrEqual(width);
      if (width === 320) {
        const mobileScan = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
          .analyze();
        expect(
          mobileScan.violations.map((v) => ({
            id: v.id,
            targets: v.nodes.slice(0, 3).map((n) => n.target),
          })),
        ).toEqual([]);
      }
      await page.screenshot({
        path: `test-results/${route === "/" ? "overview" : "replay"}-${width}.png`,
        fullPage: true,
      });
    }
  });

test("keyboard selection, mobile evidence sheet and focus restoration", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto("/replay?date=2026-01-16&rule=d1-0900");
  const slider = page.getByRole("slider");
  await expect(slider).toBeVisible();
  await slider.focus();
  await slider.press("ArrowRight");
  await expect(page).toHaveURL(/interval=2/);
  const trigger = page
    .getByRole("button", { name: "Inspect interval 2", exact: true })
    .last();
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("Interval 2 uses");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("custom cutoff validation and exact-cutoff URL restore", async ({
  page,
}) => {
  await page.goto("/replay?date=2026-01-16&rule=d1-0900");
  await page.getByText("Custom cutoff", { exact: true }).click();
  await page.getByLabel("Exact decision time (UTC)").fill("not-a-date");
  await page.getByRole("button", { name: "Apply cutoff" }).click();
  await expect(page.getByRole("alert")).toContainText("valid UTC instant");
  await page
    .getByLabel("Exact decision time (UTC)")
    .fill("2026-01-15T12:00:00Z");
  await page.getByRole("button", { name: "Apply cutoff" }).click();
  await expect(page).toHaveURL(/cutoff=2026-01-15T12/);
  await expect(page.locator(".replay-heading")).toContainText("explicit");
  await page.reload();
  await expect(page.locator(".replay-heading")).toContainText("explicit");
});

test("copy receipt keeps response and HTTP evidence separate", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("/replay?date=2026-01-16&rule=d1-0900");
  await page.getByText("Result receipt & provenance", { exact: true }).click();
  await page.getByRole("button", { name: "Copy diagnostic receipt" }).click();
  await expect(page.getByText("Copied", { exact: true })).toBeVisible();
  const receipt = JSON.parse(
    await page.evaluate(() => navigator.clipboard.readText()),
  );
  expect(receipt.response.query.deliveryDate).toBe("2026-01-16");
  expect(receipt.httpHeaders["Server-Timing"]).toContain("total;dur=");
});

test("degraded readiness remains distinguishable from an analysis failure", async ({
  page,
}) => {
  await page.goto("/?mockHealth=DEGRADED");
  await expect(page.locator(".health")).toContainText("Degraded");
  await expect(page.getByRole("heading", { name: /How far/ })).toBeVisible();
});
