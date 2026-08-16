import Foundation

enum PushUpStatus: String {
    case top
    case descending
    case bottom
    case ascending
    case unknown
}

struct PushUpFrameResult {
    let frameIndex: Int
    let status: PushUpStatus
    let rawStatusCandidate: PushUpStatus?
    let candidateStatus: PushUpStatus?
    let candidateStatusCount: Int
    let statusFrameCount: Int
    let rep: Int
    let done: Bool
    let cameraViewEstimate: String
    let selectedDepthSignal: String
    let depthSignalReliable: Bool
    let pushDepthNorm: Double?
    let pushDepthDeltaNorm: Double?
    let elbowAngleDeltaDegrees: Double?
    let leftElbowAngleDegrees: Double?
    let rightElbowAngleDegrees: Double?
    let avgElbowAngleDegrees: Double?
    let observedMinElbowAngleDegrees: Double?
    let observedMaxElbowAngleDegrees: Double?
    let effectiveTopElbowThreshold: Double?
    let effectiveBottomElbowThreshold: Double?
    let bodyLineAngleDegrees: Double?
    let hipLineDeviationNorm: Double?
    let currentRepMaxDepthNorm: Double?
    let currentRepMinElbowAngleDegrees: Double?
    let repStarted: Bool
    let sawDescending: Bool
    let sawAscending: Bool
    let lastCompletedRepSummary: PushUpRepSummary?

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
            "camera_view_estimate": cameraViewEstimate,
            "selected_depth_signal": selectedDepthSignal,
            "depth_signal_reliable": depthSignalReliable,
            "push_depth_norm": jsonValue(pushDepthNorm),
            "push_depth_delta_norm": jsonValue(pushDepthDeltaNorm),
            "elbow_angle_delta_degrees": jsonValue(elbowAngleDeltaDegrees),
            "left_elbow_angle_degrees": jsonValue(leftElbowAngleDegrees),
            "right_elbow_angle_degrees": jsonValue(rightElbowAngleDegrees),
            "avg_elbow_angle_degrees": jsonValue(avgElbowAngleDegrees),
            "observed_min_elbow_angle_degrees": jsonValue(observedMinElbowAngleDegrees),
            "observed_max_elbow_angle_degrees": jsonValue(observedMaxElbowAngleDegrees),
            "effective_top_elbow_threshold": jsonValue(effectiveTopElbowThreshold),
            "effective_bottom_elbow_threshold": jsonValue(effectiveBottomElbowThreshold),
            "body_line_angle_degrees": jsonValue(bodyLineAngleDegrees),
            "hip_line_deviation_norm": jsonValue(hipLineDeviationNorm),
            "current_rep_max_depth_norm": jsonValue(currentRepMaxDepthNorm),
            "current_rep_min_elbow_angle_degrees": jsonValue(currentRepMinElbowAngleDegrees),
            "rep_started": repStarted,
            "saw_descending": sawDescending,
            "saw_ascending": sawAscending,
            "last_completed_rep_summary": lastCompletedRepSummary.map { $0.dictionary as Any } ?? NSNull(),
        ]
    }

    private func jsonValue(_ value: Double?) -> Any {
        value.map { $0 as Any } ?? NSNull()
    }
}

struct PushUpRepSummary {
    let repIndex: Int
    let startFrame: Int
    let bottomFrame: Int?
    let endFrame: Int?
    let maxDepthNorm: Double
    let minElbowAngleDegrees: Double?
    let bodyLineAngleDegrees: Double?
    let maxHipLineDeviationNorm: Double?
    let warnings: [String]

    var dictionary: [String: Any] {
        [
            "rep_index": repIndex,
            "start_frame": startFrame,
            "bottom_frame": bottomFrame.map { $0 as Any } ?? NSNull(),
            "end_frame": endFrame.map { $0 as Any } ?? NSNull(),
            "max_depth_norm": maxDepthNorm,
            "min_elbow_angle_degrees": minElbowAngleDegrees.map { $0 as Any } ?? NSNull(),
            "body_line_angle_degrees": bodyLineAngleDegrees.map { $0 as Any } ?? NSNull(),
            "max_hip_line_deviation_norm": maxHipLineDeviationNorm.map { $0 as Any } ?? NSNull(),
            "warnings": warnings,
        ]
    }
}

struct PushUpSessionSummary {
    let completedRepCount: Int
    let repCount: Int
    let avgMaxDepthNorm: Double?
    let maxDepthNorm: Double?
    let minElbowAngleDegrees: Double?

    var dictionary: [String: Any] {
        [
            "completed_rep_count": completedRepCount,
            "rep_count": repCount,
            "avg_max_depth_norm": avgMaxDepthNorm.map { $0 as Any } ?? NSNull(),
            "max_depth_norm": maxDepthNorm.map { $0 as Any } ?? NSNull(),
            "min_elbow_angle_degrees": minElbowAngleDegrees.map { $0 as Any } ?? NSNull(),
        ]
    }
}
