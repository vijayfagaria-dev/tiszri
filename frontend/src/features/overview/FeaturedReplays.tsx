import { Link } from "react-router-dom";
import {
  ChevronRight,
  Clock3,
  Info,
  Sparkles,
  Star,
  TriangleAlert,
} from "lucide-react";
import type { Metadata, Summary } from "../../api/schemas";
import { dateLabel } from "../../lib/format";
import { replayLink } from "../../app/url";
const featuredCopy: Record<
  string,
  { title: string; text: string; Icon: typeof Star; color: string }
> = {
  WORST_DAY: {
    title: "Worst day",
    text: "Largest typical miss in the window",
    Icon: TriangleAlert,
    color: "amber",
  },
  BEST_DAY: {
    title: "Best day",
    text: "Lowest MAE among complete days",
    Icon: Star,
    color: "teal",
  },
  BIAS_HIDES_ERROR: {
    title: "Bias hides error",
    text: "Opposite errors cancelled out",
    Icon: Sparkles,
    color: "purple",
  },
  OFF_SCHEDULE_VINTAGE: {
    title: "Off-schedule forecast",
    text: "Explore the publication evidence",
    Icon: Clock3,
    color: "cyan",
  },
};
export function FeaturedReplays({
  data,
  metadata,
  search,
}: {
  data: Summary;
  metadata: Metadata;
  search: URLSearchParams;
}) {
  return (
    data.featured.length > 0 && (
      <section className="featured">
        <h2>
          <Sparkles size={17} />
          Featured replays <span>A few days worth a closer look</span>
        </h2>
        <div className="featured-grid">
          {data.featured.map((f) => {
            const { title, text, Icon, color } = featuredCopy[f.kind] ?? {
              title: "Other",
              text: "Explore this featured replay",
              Icon: Info,
              color: "cyan",
            };
            return (
              <Link
                key={f.kind}
                className={`feature-card ${color}`}
                to={replayLink(
                  f.deliveryDate,
                  f.suggestedRule,
                  metadata,
                  search,
                )}
              >
                <span className="icon-orb">
                  <Icon size={22} />
                </span>
                <div>
                  <h3>
                    {title} <span>· {dateLabel(f.deliveryDate)}</span>
                  </h3>
                  <p>{text}</p>
                </div>
                <ChevronRight className="feature-arrow" size={17} />
              </Link>
            );
          })}
        </div>
      </section>
    )
  );
}
