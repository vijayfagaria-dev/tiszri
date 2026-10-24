import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  daySchema,
  summarySchema,
  metadataSchema,
  readySchema,
  type DayAnalysis,
  type Summary,
} from "./schemas";
import { request, type ApiResult } from "./client";
export const useMetadata = () =>
  useQuery({
    queryKey: ["metadata"],
    queryFn: ({ signal }) => request("metadata", metadataSchema, signal),
    staleTime: Infinity,
  });
export const useHealth = () =>
  useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) =>
      request("health/ready", readySchema, signal, undefined, undefined, [503]),
    refetchInterval: 60000,
  });
export function useAnalysis(
  params: URLSearchParams,
  replay: boolean,
  scenarioKey: string,
  problem?: Error,
) {
  const queryClient = useQueryClient();
  return useQuery<ApiResult<DayAnalysis | Summary>>({
    queryKey: [
      replay ? "day" : "summary",
      params.toString(),
      scenarioKey,
      problem?.message,
    ],
    queryFn: ({ signal }) => {
      if (problem) throw problem;
      // An analysis is what contacts Elexon, so refresh the source status once it settles.
      const refreshHealth = () =>
        void queryClient.invalidateQueries({ queryKey: ["health"] });
      const ruleMatches = (
        rule: { dayOffset: number; localTime: string } | null,
      ) =>
        rule?.dayOffset === Number(params.get("cutoffDayOffset")) &&
        rule?.localTime === params.get("cutoffLocalTime");
      return (
        replay
          ? request(
              "wind-analysis",
              daySchema,
              signal,
              params,
              (d) =>
                d.query.deliveryDate === params.get("deliveryDate") &&
                (params.has("decisionCutoff")
                  ? d.query.decisionCutoff.utc === params.get("decisionCutoff")
                  : ruleMatches(d.query.decisionCutoff.rule)),
            )
          : request(
              "accuracy-summary",
              summarySchema,
              signal,
              params,
              (d) =>
                d.query.from === params.get("from") &&
                d.query.to === params.get("to") &&
                ruleMatches(d.query.rule),
            )
      ).finally(refreshHealth);
    },
    staleTime: 300000,
    placeholderData: keepPreviousData,
  });
}
