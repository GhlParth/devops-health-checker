import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="DevOps Infrastructure Health Checker"
    )

    parser.add_argument(
        "--github",
        action="store_true",
        help="Run GitHub health check",
    )

    parser.add_argument(
        "--aws",
        action="store_true",
        help="Run AWS health check",
    )

    parser.add_argument(
        "--kubernetes",
        action="store_true",
        help="Run Kubernetes health check",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all health checks",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    print("DevOps Infrastructure Health Checker")

    if args.github:
        print("Running GitHub health check")

    if args.aws:
        print("Running AWS health check")

    if args.kubernetes:
        print("Running Kubernetes health check")

    if args.all:
        print("Running all health checks")


if __name__ == "__main__":
    main()