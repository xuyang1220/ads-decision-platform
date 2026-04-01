class DecisionEngine:
    def __init__(
        self,
        predictor: CTRPredictor,
        landscape_model: BidLandscapeModel,
        budget_state_provider,
        rank_scorer: RankScorer,
        allocator: MultiSlotAllocator,
    ):
        self.predictor = predictor
        self.landscape_model = landscape_model
        self.budget_state_provider = budget_state_provider
        self.rank_scorer = rank_scorer
        self.allocator = allocator

    def decide(self, auction_input: AuctionInput, num_slots: int) -> AuctionResult:
        scored = []

        for candidate in auction_input.candidates:
            pred = self.predictor.predict(auction_input.request, candidate)

            budget_state = self.budget_state_provider.get_state(candidate.campaign_id)
            directive = budget_state.current_directive

            lc = LandscapeContext(
                campaign_id=candidate.campaign_id,
                adgroup_id=candidate.adgroup_id,
                segment_id=candidate.extra.get("segment_id"),
                channel=auction_input.request.placement,
            )

            est = self.landscape_model.estimate(
                bid=candidate.base_bid * directive.pacing_multiplier,
                context=lc,
            )

            scored_candidate = self.rank_scorer.score(
                candidate=candidate,
                prediction=pred,
                directive=directive,
                landscape=est,
            )
            scored.append(scored_candidate)

        return self.allocator.allocate(scored, num_slots=num_slots)