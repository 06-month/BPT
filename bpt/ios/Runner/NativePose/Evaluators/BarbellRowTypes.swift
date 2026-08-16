import Foundation

enum BarbellRowStatus: String {
    case bottom
    case pulling
    case top
    case lowering
    case unknown
}

struct BarbellRowFrameResult {
    let frameIndex: Int
    let status: BarbellRowStatus
    let rawStatusCandidate: BarbellRowStatus?
    let candidateStatus: BarbellRowStatus?
    let candidateStatusCount: Int
    let statusFrameCount: Int
    let rep: Int
    let done: Bool
    let rowDepthNorm: Double?
    let rowDepthDeltaNorm: Double?
    let leftElbowAngleDegrees: Double?
    let rightElbowAngleDegrees: Double?
    let avgElbowAngleDegrees: Double?
    let torsoLeanAngleDegrees: Double?
    let currentRepMaxRowDepthNorm: Double?
    let currentRepMinElbowAngleDegrees: Double?
    let repStarted: Bool
    let sawPulling: Bool
    let sawLowering: Bool
    let lastCompletedRepSummary: BarbellRowRepSummary?

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
            "row_depth_norm": jsonValue(rowDepthNorm),
            "row_depth_delta_norm": jsonValue(rowDepthDeltaNorm),
            "left_elbow_angle_degrees": jsonValue(leftElbowAngleDegrees),
            "right_elbow_angle_degrees": jsonValue(rightElbowAngleDegrees),
            "avg_elbow_angle_degrees": jsonValue(avgElbowAngleDegrees),
            "torso_lean_angle_degrees": jsonValue(torsoLeanAngleDegrees),
            "current_rep_max_row_depth_norm": jsonValue(currentRepMaxRowDepthNorm),
            "current_rep_min_elbow_angle_degrees": jsonValue(currentRepMinElbowAngleDegrees),
            "rep_started": repStarted,
            "saw_pulling": sawPulling,
            "saw_lowering": sawLowering,
            "last_completed_rep_summary": lastCompletedRepSummary.map { $0.dictionary as Any } ?? NSNull(),
        ]
    }

    private func jsonValue(_ value: Double?) -> Any {
        value.map { $0 as Any } ?? NSNull()
    }
}

struct BarbellRowRepSummary {
    let repIndex: Int
    let startFrame: Int
    let topFrame: Int?
    let endFrame: Int?
    let maxRowDepthNorm: Double
    let minElbowAngleDegrees: Double?
    let warnings: [String]

    var dictionary: [String: Any] {
        [
            "rep_index": repIndex,
            "start_frame": startFrame,
            "top_frame": topFrame.map { $0 as Any } ?? NSNull(),
            "end_frame": endFrame.map { $0 as Any } ?? NSNull(),
            "max_row_depth_norm": maxRowDepthNorm,
            "min_elbow_angle_degrees": minElbowAngleDegrees.map { $0 as Any } ?? NSNull(),
            "warnings": warnings,
        ]
    }
}

struct BarbellRowSessionSummary {
    let completedRepCount: Int
    let repCount: Int
    let avgMaxRowDepthNorm: Double?
    let minElbowAngleDegrees: Double?
    let maxRowDepthNorm: Double?

    var dictionary: [String: Any] {
        [
            "completed_rep_count": completedRepCount,
            "rep_count": repCount,
            "avg_max_row_depth_norm": avgMaxRowDepthNorm.map { $0 as Any } ?? NSNull(),
            "min_elbow_angle_degrees": minElbowAngleDegrees.map { $0 as Any } ?? NSNull(),
            "max_row_depth_norm": maxRowDepthNorm.map { $0 as Any } ?? NSNull(),
        ]
    }
}
