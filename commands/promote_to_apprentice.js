// Command to promote kits to apprentices

const promoteToApprentice = (kitID, mentorID) => {
    // Logic to promote kit to apprentice
    const kit = getKitByID(kitID);
    const mentor = getMentorByID(mentorID);

    if (kit && mentor) {
        kit.status = 'apprentice';
        kit.mentor = mentor;
        saveKit(kit);
        return `Kit ${kitID} has been promoted to apprentice under mentor ${mentorID}.`;
    } else {
        return 'Kit or mentor not found.';
    }
};

module.exports = { promoteToApprentice };