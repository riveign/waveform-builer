import type { TinderQueueItem, TinderDecision, TinderRetrainResult, TinderBatchDecision } from '$lib/types';
import { getTinderQueue, submitDecision, submitBatchDecisions, retrain, type TinderQueueParams } from '$lib/api/tinder';

let queue = $state<TinderQueueItem[]>([]);
let queueTotal = $state(0);
let currentIndex = $state(0);
let loading = $state(false);
let error = $state<string | null>(null);

// Session counters (reset on each load)
let sessionConfirmed = $state(0);
let sessionOverridden = $state(0);
let sessionSkipped = $state(0);
let lastTeachingMoment = $state<string | null>(null);
let retrainResult = $state<TinderRetrainResult | null>(null);
let retraining = $state(false);

async function loadQueue(params: TinderQueueParams = {}) {
	loading = true;
	error = null;
	try {
		const result = await getTinderQueue(params);
		queue = result.items;
		queueTotal = result.total;
		currentIndex = 0;
		sessionConfirmed = 0;
		sessionOverridden = 0;
		sessionSkipped = 0;
		lastTeachingMoment = null;
		retrainResult = null;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
		queue = [];
		queueTotal = 0;
	} finally {
		loading = false;
	}
}

async function decide(decision: TinderDecision, overrideZone?: string) {
	const item = queue[currentIndex];
	if (!item) return;

	try {
		const result = await submitDecision(item.track.id, decision, overrideZone);
		if (decision === 'confirm') sessionConfirmed++;
		else if (decision === 'override') sessionOverridden++;
		else sessionSkipped++;

		lastTeachingMoment = result.teaching_moment;
		currentIndex++;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

async function decideBatch(decisions: TinderBatchDecision[]) {
	const batchSize = decisions.length;
	// Only send non-skip decisions to the API
	const toSubmit = decisions.filter(d => d.decision !== 'skip');
	const skipCount = batchSize - toSubmit.length;

	try {
		if (toSubmit.length > 0) {
			const result = await submitBatchDecisions(toSubmit);
			for (const r of result.results) {
				if (r.decision === 'confirm') sessionConfirmed++;
				else if (r.decision === 'override') sessionOverridden++;
			}
			lastTeachingMoment = result.results.find(r => r.teaching_moment)?.teaching_moment ?? null;
		}
		sessionSkipped += skipCount;
		// Advance past the entire batch page
		currentIndex += batchSize;
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	}
}

async function triggerRetrain() {
	retraining = true;
	error = null;
	try {
		retrainResult = await retrain();
	} catch (e) {
		error = e instanceof Error ? e.message : String(e);
	} finally {
		retraining = false;
	}
}

export function getTinderStore() {
	return {
		get queue() { return queue; },
		get queueTotal() { return queueTotal; },
		get currentIndex() { return currentIndex; },
		get currentItem() { return queue[currentIndex] ?? null; },
		get isComplete() { return currentIndex >= queue.length && queue.length > 0; },
		get loading() { return loading; },
		get error() { return error; },
		get sessionConfirmed() { return sessionConfirmed; },
		get sessionOverridden() { return sessionOverridden; },
		get sessionSkipped() { return sessionSkipped; },
		get sessionTotal() { return sessionConfirmed + sessionOverridden + sessionSkipped; },
		get lastTeachingMoment() { return lastTeachingMoment; },
		get retrainResult() { return retrainResult; },
		get retraining() { return retraining; },
		loadQueue,
		decide,
		decideBatch,
		triggerRetrain,
	};
}
