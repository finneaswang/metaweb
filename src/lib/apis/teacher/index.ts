import { WEBUI_API_BASE_URL } from "$lib/constants";

////////////////////////////
// Types
////////////////////////////

export interface TeacherAIRequest {
    student_id: string;
    question: string;
    context?: string;
}

export interface DataSource {
    conversation_count: number;
    assignment_count: number;
    profile_date?: number;
    date_range: string;
}

export interface TeacherAIResponse {
    answer: string;
    data_sources: DataSource;
    student_name: string;
}

export interface StudentInfo {
    id: string;
    name: string;
    email: string;
    last_active_at: number;
    role: string;
}

////////////////////////////
// API Functions
////////////////////////////

export const askTeacherAI = async (
    token: string,
    request: TeacherAIRequest
): Promise<TeacherAIResponse> => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/teacher/ask-ai`, {
        method: "POST",
        headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
            authorization: `Bearer ${token}`
        },
        body: JSON.stringify(request)
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to ask teacher AI");
    }

    return res.json();
};

export const getStudentList = async (token: string): Promise<StudentInfo[]> => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/teacher/students`, {
        method: "GET",
        headers: {
            Accept: "application/json",
            authorization: `Bearer ${token}`
        }
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to get student list");
    }

    return res.json();
};
