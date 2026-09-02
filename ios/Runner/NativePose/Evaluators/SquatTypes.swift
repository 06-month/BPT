import Foundation

enum SquatStatus: String {
    case top
    case descending
    case bottom
    case ascending
    case unknown
}

struct SquatFrameResult {
    let frameIndex: Int
    let status: SquatStatus
    let rawStatusCandidate: SquatStatus?
    let candidateStatus: SquatStatus?
    let candidateStatusCount: Int
    let statusFrameCount: Int
    let rep: Int
    let done: Bool
    let squatDepthNorm: Double?
    let squatDepthDeltaNorm: Double?
    let leftKneeAngleDegrees: Double?
    let rightKneeAngleDegrees: Double?
    let avgKneeAngleDegrees: Double?
    let hipCenterY: Double?
    let kneeCenterY: Double?
    let ankleCenterY: Double?
    let currentRepMaxDepthNorm: Double?
    let currentRepMinKneeAngleDegrees: Double?
    let lastCompletedRepSummary: SquatRepSummary?

    var dictionary: [String: Any] {
        [
            "frame_index": frameIndex,
            "status": status.rawValue,
            "raw_status_candidate": rawStatusCandidate.map { $0.rawValue as Any } ?? NSNull(),
            "candidate_status": candidateStatus.map { $0.rawValue as Any } ?? NSNull(),
            "candidate_status_count": candidateStatusCount,
            "status_frame_count": statusFrameCount,
            "rep": rep,
            "done": done,
            "squat_depth_norm": jsonValue(squatDepthNorm),
            "squat_depth_delta_norm": jsonValue(squatDepthDeltaNorm),
            "left_knee_angle_degrees": jsonValue(leftKneeAngleDegrees),
            "right_knee_angle_degrees": jsonValue(rightKneeAngleDegrees),
            "avg_knee_angle_degrees": jsonValue(avgKneeAngleDegrees),
            "hip_center_y": jsonValue(hipCenterY),
            "knee_center_y": jsonValue(kneeCenterY),
            "ankle_center_y": jsonValue(ankleCenterY),
            "current_rep_max_depth_norm": jsonValue(currentRepMaxDepthNorm),
            "current_rep_min_knee_angle_degrees": jsonValue(currentRepMinKneeAngleDegrees),
            "last_completed_rep_summary": lastCompletedRepSummary.map { $0.dictionary as Any } ?? NSNull(),
        ]
    }

    private func jsonValue(_ value: Double?) -> Any {
        value.map { $0 as Any } ?? NSNull()
    }
}

struct SquatRepSummary {
    let repIndex: Int
    let startFrame: Int
    let bottomFrame: Int?
    let endFrame: Int?
    let maxDepthNorm: Double
    let minKneeAngleDegrees: Double?
    let warnings: [String]

    var dictionary: [String: Any] {
        [
            "rep_index": repIndex,
            "start_frame": startFrame,
            "bottom_frame": bottomFrame.map { $0 as Any } ?? NSNull(),
            "end_frame": endFrame.map { $0 as Any } ?? NSNull(),
            "max_depth_norm": maxDepthNorm,
            "min_knee_angle_degrees": minKneeAngleDegrees.map { $0 as Any } ?? NSNull(),
            "warnings": warnings,
        ]
    }
}

struct SquatSessionSummary {
    let completedRepCount: Int
    let repCount: Int
    let avgMaxDepthNorm: Double?
    let minKneeAngleDegrees: Double?
    let maxDepthNorm: Double?

    var dictionary: [String: Any] {
        [
            "completed_rep_count": completedRepCount,
            "rep_count": repCount,
            "avg_max_depth_norm": avgMaxDepthNorm.map { $0 as Any } ?? NSNull(),
            "min_knee_angle_degrees": minKneeAngleDegrees.map { $0 as Any } ?? NSNull(),
            "max_depth_norm": maxDepthNorm.map { $0 as Any } ?? NSNull(),
        ]
    }
}
