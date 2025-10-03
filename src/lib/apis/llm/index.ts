import { WEBUI_API_BASE_URL } from '$lib/constants';

/**
 * LLM Proxy API
 * 统一代理所有LLM请求，记录sessions和turns用于画像分析
 */

export interface ProxyMessageRequest {
	message: string;
	chat_id?: string;
	assignment_id?: string;
	mode?: 'chat' | 'homework' | 'deep_think';
	model?: string;
	meta?: Record<string, any>;
}

export interface ProxyMessageResponse {
	turn_id: string;
	session_id: string;
	content: string;
	model: string;
	meta: Record<string, any>;
}

export interface SessionModel {
	id: string;
	user_id: string;
	assignment_id?: string;
	mode: string;
	started_at: number;
	ended_at?: number;
	policy_snapshot: Record<string, any>;
	meta: Record<string, any>;
}

export interface TurnModel {
	id: string;
	session_id: string;
	role: 'user' | 'assistant' | 'system';
	content: string;
	tool_calls: any[];
	model?: string;
	tokens_in: number;
	tokens_out: number;
	cost: number;
	created_at: number;
	meta: Record<string, any>;
}

export const sendProxyMessage = async (
	token: string,
	request: ProxyMessageRequest
): Promise<ProxyMessageResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/llm/proxy`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(request)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error('LLM Proxy error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getUserSessions = async (
	token: string,
	skip: number = 0,
	limit: number = 50
): Promise<{ sessions: SessionModel[] }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/llm/sessions?skip=${skip}&limit=${limit}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error('Get sessions error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSessionTurns = async (
	token: string,
	sessionId: string
): Promise<{ session: SessionModel; turns: TurnModel[] }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/llm/sessions/${sessionId}/turns`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error('Get session turns error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
