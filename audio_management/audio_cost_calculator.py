import time

# The $ rate per minute
COST_RATE1 = 0.0043
COST_RATE2 = 0.0036

COST_METRICS_FILE_PATH = "audio_management/metrics.txt"


class AudioCostCalculator:
    """
    Handles calculating the cost for audio requests sent to DeepGram for S2T
    """

    def __init__(self, guild):
        self.guild = guild
        self.session_start_time = 0
        self.session_end_time = 0
        self.session_costs_rate1 = 0
        self.session_costs_rate2 = 0
        self.max_single_request_cost_rate1 = 0
        self.max_single_request_cost_rate2 = 0
        self.total_requests = 0
        self.failed_requests = 0
        self.successful_requests = 0
        self.talk_time_per_person = {}  # Dictionary to track talk time per person
        self.rejected_short_audio_requests = 0  # Counter for short audio requests
        self.rejected_short_audio_requests_total_duration = 0

    def calculate_cost(self, audio_duration_seconds, user_id):
        # Two different cost rates
        audio_duration_minutes = audio_duration_seconds / 60  # Convert to minutes

        # Calculate costs for both rates
        cost1 = audio_duration_minutes * COST_RATE1
        cost2 = audio_duration_minutes * COST_RATE2

        # Update session costs for both rates
        self.session_costs_rate1 += cost1
        self.session_costs_rate2 += cost2

        # Update max single request cost for both rates
        self.max_single_request_cost_rate1 = max(self.max_single_request_cost_rate1, cost1)
        self.max_single_request_cost_rate2 = max(self.max_single_request_cost_rate2, cost2)

        # Update total and successful requests
        self.total_requests += 1
        self.successful_requests += 1

        if user_id not in self.talk_time_per_person:
            self.talk_time_per_person[user_id] = 0
        self.talk_time_per_person[user_id] += audio_duration_minutes

    def increment_failed_requests(self):
        self.failed_requests += 1
        self.successful_requests -= 1  # Adjust successful count

    def add_rejected_short_audio_request(self, audio_duration_seconds):
        self.rejected_short_audio_requests += 1
        self.rejected_short_audio_requests_total_duration += (audio_duration_seconds / 60)

    def write_talk_time_and_cost_to_file(self, file):
        # Calculate total talk time for all users
        total_talk_time_minutes = sum(self.talk_time_per_person.values())

        # Calculate cost and sort users by talk time
        sorted_users = sorted(self.talk_time_per_person.items(), key=lambda x: x[1], reverse=True)

        for user_id, talk_time_minutes in sorted_users:
            username = self.guild.get_member(int(user_id))
            cost_rate1 = talk_time_minutes * COST_RATE1
            cost_rate2 = talk_time_minutes * COST_RATE2

            # Calculate the percentage of total talk time for this user
            percentage_of_total_time = (
                                               talk_time_minutes / total_talk_time_minutes) * 100 if total_talk_time_minutes > 0 else 0

            talk_time_formatted = time.strftime('%H:%M:%S', time.gmtime(talk_time_minutes * 60))
            file.write(
                f"{username} - {talk_time_formatted} - (Cost1: ${cost_rate1:.3f}) - (Cost2: ${cost_rate2:.3f}) - "
                f"Talk Time: {percentage_of_total_time:.2f}%\n")

        file.write("\n")

    def _write_cost_metrics_for_rate(self, file, rate_label):
        total_cost = self.session_costs_rate1 if rate_label == 'Rate 1' else self.session_costs_rate2
        max_cost = self.max_single_request_cost_rate1 if rate_label == 'Rate 1' else self.max_single_request_cost_rate2
        average_cost = total_cost / self.total_requests if self.total_requests > 0 else 0

        file.write(f"Cost for rate: {rate_label}\n\n")
        file.write(f"Total Cost for Server: ${total_cost:.3f}\n")
        file.write(f"Max Cost of Single Request: ${max_cost:.5f}\n")
        file.write(f"Average Cost of a Single Request: ${average_cost:.5f}\n\n")

    def write_rejected_requests_stats_to_file(self, file, rate_label):
        rejected_requests_cost = self.rejected_short_audio_requests_total_duration * rate_label
        file.write(f"Total Cost for Rejected Requests ({rate_label}): ${rejected_requests_cost:.4f}\n\n")

    def save_cost_metrics(self):
        cost_metrics_file = COST_METRICS_FILE_PATH

        print("Calculating audio costs")
        with open(cost_metrics_file, "w") as file:
            session_duration = "Unknown"
            session_duration_time = self.session_end_time - self.session_start_time
            if session_duration_time > 0:
                session_duration = time.strftime('%H:%M:%S', time.gmtime(session_duration_time))

            file.write(f"Session Duration: {session_duration}\n")
            self._write_cost_metrics_for_rate(file, "Rate 1")
            self._write_cost_metrics_for_rate(file, "Rate 2")

            file.write(f"User audio metrics:\n")
            self.write_talk_time_and_cost_to_file(file)

            # Failed and Successful requests
            file.write(f"Total Requests: {self.total_requests}\n")
            file.write(f"Number of Failed Requests: {self.failed_requests}\n")
            file.write(f"Number of Successful Requests: {self.successful_requests}\n")

            # Percentage calculations
            if self.total_requests > 0:
                failed_percentage = (self.failed_requests / self.total_requests) * 100
                successful_percentage = (self.successful_requests / self.total_requests) * 100
                file.write(f"Percentage of Failed Requests: {failed_percentage:.2f}%\n")
                file.write(f"Percentage of Successful Requests: {successful_percentage:.2f}%\n\n")
            else:
                print("Kind of strange. No requests were sent during this session")

            total_rejected_duration_formatted = time.strftime('%H:%M:%S', time.gmtime(
                self.rejected_short_audio_requests_total_duration * 60))
            file.write(f"Total Rejected Short Audio Requests: {self.rejected_short_audio_requests}\n")
            file.write(f"Total Duration of Rejected Requests: {total_rejected_duration_formatted}\n\n")

            self.write_rejected_requests_stats_to_file(file, COST_RATE1)
            self.write_rejected_requests_stats_to_file(file, COST_RATE2)
