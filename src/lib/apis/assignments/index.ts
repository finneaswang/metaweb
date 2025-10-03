import { WEBUI_API_BASE_URL } from "$lib/constants";

type AssignmentItem = {
	title: string;
	description?: string;
	due_date: string;
	status?: string;
	access_control?: null | object;
};

export const createNewAssignment = async (token: string, assignment: AssignmentItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/create`, {
		method: "POST",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...assignment
		})
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

export const getAssignments = async (token: string = "") => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/`, {
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

export const getAssignmentList = async (token: string = "", page: number | null = null) => {
	let error = null;
	const searchParams = new URLSearchParams();

	if (page !== null) {
		searchParams.append("page", `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/list?${searchParams.toString()}`, {
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

export const getAssignmentById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/${id}`, {
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

export const updateAssignmentById = async (token: string, id: string, assignment: Partial<AssignmentItem>) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/${id}/update`, {
		method: "POST",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...assignment
		})
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

export const submitAssignment = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/${id}/submit`, {
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

export const deleteAssignmentById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/${id}/delete`, {
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


export interface AssignmentStatistics {
    assignment_id: string;
    total_students: number;
    submitted_count: number;
    graded_count: number;
    submission_rate: number;
    avg_score: number;
    max_score: number;
    min_score: number;
    grade_distribution: {
        A: number;
        B: number;
        C: number;
        D: number;
        F: number;
    };
}

export const getAssignmentStatistics = async (
    token: string,
    id: string
): Promise<AssignmentStatistics> => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/${id}/statistics`, {
        method: "GET",
        headers: {
            Accept: "application/json",
            authorization: `Bearer ${token}`
        }
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to get assignment statistics");
    }

    return res.json();
};

export const exportAssignmentGrades = async (token: string, id: string): Promise<Blob> => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/assignments/${id}/export`, {
        method: "GET",
        headers: {
            authorization: `Bearer ${token}`
        }
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to export grades");
    }

    return res.blob();
};
