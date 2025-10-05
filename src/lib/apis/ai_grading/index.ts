const API_BASE_URL = ''  // Will be set by environment

export const requestAIGrading = async (token: string, submissionId: string) => {
	let error = null;

	const res = await fetch(`/api/v1/ai-grading/${submissionId}/ai-grade`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export type AIGradeResponse = {
	rubric_scores: Record<string, number>;
	feedback_draft: string;
	total_score: number;
	confidence: number;
};
