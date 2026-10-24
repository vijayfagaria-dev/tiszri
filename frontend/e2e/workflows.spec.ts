import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("overview to replay, selection, filters and history", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /How far/ })).toBeVisible();
  await expect(page).toHaveURL(/rule=d1-0900/);
  await expect(page.locator(".planning")).toContainText(
    "no more than 4,145 MW below the forecast",
  );
  await page.getByRole("button", { name: "Ranked", exact: true }).click();
  await expect(page.getByText("Highest MAE first")).toBeVisible();
  await page.getByRole("link", { name: /Worst day/ }).click();
  await expect(
    page.getByRole("heading", { name: "Forecast vs actual" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Inspect interval 24", exact: true })
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
  await expect(page.locator(".callout")).toContainText("Partial coverage");
  await page
    .getByRole("button", { name: "Not published 4", exact: true })
    .click();
  await expect(page.locator("tbody tr")).toHaveCount(4);
  await page.goto("/replay?date=2026-01-15&rule=custom:-3:09:00");
  await expect(
    page.getByRole("heading", { name: "No forecast had been published yet" }),
  ).toBeVisible();
  await expect(page.locator(".empty-panel")).toContainText(
    "The first one was published on Tue 13 Jan at 02:30 GMT.",
  );
  await expect(page.locator(".callout")).toHaveCount(0);
  await page.goto("/replay?date=2026-01-16&rule=d1-0900");
  await page.getByLabel("Demo scenario").selectOption("edge");
  await page.getByRole("button", { name: "All 48", exact: true }).click();
  await expect(page.locator("tbody")).toContainText("Ambiguous forecast");
  await page.goto("/replay?date=2026-01-16&rule=after-0000");
  await expect(page.getByText("Hindsight view", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Switch to day before, 09:00" })
    .click();
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
  const picker = page.getByRole("combobox", {
    name: "Decision time",
    exact: true,
  });
  await expect(picker).toBeVisible();
  await picker.selectOption("d1-1200");
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
  // The ledger row has the same name, so target the sheet's own button and
  // wait for it to re-render with the new interval before opening it.
  const trigger = page.locator(".mobile-inspector-trigger");
  await expect(trigger).toHaveText("Inspect interval 2");
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("Interval 2 uses");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("custom decision time and exact-cutoff URL restore", async ({ page }) => {
  await page.goto("/replay?date=2026-01-15&rule=d1-0900");
  await page
    .getByRole("combobox", { name: "Decision time", exact: true })
    .selectOption("custom");
  await expect(page).toHaveURL(/rule=custom%3A-1%3A09%3A00/);
  await page.getByLabel("Decision day").selectOption("-3");
  await expect(page).toHaveURL(/rule=custom%3A-3%3A09%3A00/);
  await expect(page.locator(".replay-heading")).toContainText(
    "Mon 12 Jan at 09:00 GMT",
  );
  await page.goto("/replay?date=2026-01-16&cutoff=2026-01-15T12%3A00%3A00Z");
  await expect(page.locator(".replay-heading")).toContainText("exact time");
  await expect(page.locator(".forecast-used")).toContainText(
    "published Thu 15 Jan at 09:30 GMT",
  );
  await expect(page.getByLabel("Decision day")).toHaveValue("-1");
  await expect(page.getByLabel("Time (UK)")).toHaveValue("12:00");
});

test("degraded readiness remains distinguishable from an analysis failure", async ({
  page,
}) => {
  await page.goto("/?mockHealth=DEGRADED");
  await expect(page.locator(".health")).toContainText("Degraded");
  await expect(page.getByRole("heading", { name: /How far/ })).toBeVisible();
});

test("info tips show on hover or focus and close on leave, outside click or Escape", async ({
  page,
}) => {
  await page.goto("/");
  const info = page.getByRole("button", { name: "About Typical miss" });
  const tip = page.getByRole("tooltip");
  await info.hover();
  await expect(tip).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(tip).toBeHidden();
  await info.focus();
  await expect(tip).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(tip).toBeHidden();
  await info.click();
  await expect(tip).toBeVisible();
  await page.locator(".app-footer").click();
  await expect(tip).toBeHidden();
});
