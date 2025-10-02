import { WEBUI_API_BASE_URL } from "$lib/constants";

type SubmissionItem = {
	assignment_id: string;
	content?: string;
	attachments?: any[];
};

type SubmissionUpdateItem = {
	content?: string;
	attachments?: any[];
	status?: string;
	score?: number;
	grade?: string;
	feedback?: string;
};

export const createSubmission = async (token: string, submission: SubmissionItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/submissions/create`, {
		method: "POST",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(submission)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSubmissions = async (token: string = "") => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/submissions/`, {
		method: "GET",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSubmissionsByAssignmentId = async (token: string, assignmentId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/submissions/assignment/${assignmentId}`, {
		method: "GET",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSubmissionById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/submissions/${id}`, {
		method: "GET",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateSubmissionById = async (token: string, id: string, submission: SubmissionUpdateItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/submissions/${id}/update`, {
		method: "POST",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(submission)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const submitSubmission = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/submissions/${id}/submit`, {
		method: "POST",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const gradeSubmission = async (token: string, id: string, grade: { score: number; grade?: string; feedback?: string }) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/submissions/${id}/grade`, {
		method: "POST",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(grade)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteSubmissionById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/submissions/${id}/delete`, {
		method: "DELETE",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
