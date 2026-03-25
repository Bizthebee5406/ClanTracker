// Updated /assign_mentor command
if (mentor.rank !== "warrior") {
    throw new Error("The mentor must be a full warrior to mentor an apprentice.");
}